"""
:copyright: 2010-2015 by Ronny Pfannschmidt
:license: MIT
"""
import os
import warnings

from .config import Configuration
from .utils import function_has_arg, string_types
from .version import format_version, meta
from .discover import iter_matching_entrypoints

PRETEND_KEY = "SETUPTOOLS_SCM_PRETEND_VERSION"

TEMPLATES = {
    ".py": """\
# coding: utf-8
# file generated by setuptools_scm
# don't change, don't track in version control
version = {version!r}
""",
    ".txt": "{version}",
}


def version_from_scm(root):
    warnings.warn(
        "version_from_scm is deprecated please use get_version",
        category=DeprecationWarning,
    )
    config = Configuration()
    config.root = root
    # TODO: Is it API?
    return _version_from_entrypoint(config, "setuptools_scm.parse_scm")


def _call_entrypoint_fn(config, fn):
    if function_has_arg(fn, "config"):
        return fn(config.absolute_root, config=config)
    else:
        warnings.warn(
            "parse functions are required to provide a named argument"
            " 'config' in the future.",
            PendingDeprecationWarning,
        )
        return fn(config.absolute_root)


def _version_from_entrypoint(config, entrypoint):
    for ep in iter_matching_entrypoints(config.absolute_root, entrypoint):
        version = _call_entrypoint_fn(config, ep.load())

        if version:
            return version


def dump_version(root, version, write_to, template=None):
    assert isinstance(version, string_types)
    if not write_to:
        return
    target = os.path.normpath(os.path.join(root, write_to))
    ext = os.path.splitext(target)[1]
    template = template or TEMPLATES.get(ext)

    if template is None:
        raise ValueError(
            "bad file format: '{}' (of {}) \nonly *.txt and *.py are supported".format(
                os.path.splitext(target)[1], target
            )
        )
    with open(target, "w") as fp:
        fp.write(template.format(version=version))


def _do_parse(config):
    pretended = os.environ.get(PRETEND_KEY)
    if pretended:
        # we use meta here since the pretended version
        # must adhere to the pep to begin with
        return meta(tag=pretended, preformatted=True)

    if config.parse:
        parse_result = _call_entrypoint_fn(config, config.parse)
        if isinstance(parse_result, string_types):
            raise TypeError(
                "version parse result was a string\nplease return a parsed version"
            )
        version = parse_result or _version_from_entrypoint(
            config, "setuptools_scm.parse_scm_fallback"
        )
    else:
        # include fallbacks after dropping them from the main entrypoint
        version = _version_from_entrypoint(
            config, "setuptools_scm.parse_scm"
        ) or _version_from_entrypoint(
            config, "setuptools_scm.parse_scm_fallback"
        )

    if version:
        return version

    raise LookupError(
        "setuptools-scm was unable to detect version for %r.\n\n"
        "Make sure you're either building from a fully intact git repository "
        "or PyPI tarballs. Most other sources (such as GitHub's tarballs, a "
        "git checkout without the .git folder) don't contain the necessary "
        "metadata and will not work.\n\n"
        "For example, if you're using pip, instead of "
        "https://github.com/user/proj/archive/master.zip "
        "use git+https://github.com/user/proj.git#egg=proj" % config.absolute_root
    )


def get_version(
    root=".",
    version_scheme="guess-next-dev",
    local_scheme="node-and-date",
    write_to=None,
    write_to_template=None,
    relative_to=None,
    tag_regex=None,
    parse=None,
):
    """
    If supplied, relative_to should be a file from which root may
    be resolved. Typically called by a script or module that is not
    in the root of the repository to direct setuptools_scm to the
    root of the repository by supplying ``__file__``.
    """

    config = Configuration()
    config.root = root
    config.version_scheme = version_scheme
    config.local_scheme = local_scheme
    config.write_to = write_to
    config.write_to_template = write_to_template
    config.relative_to = relative_to
    config.tag_regex = tag_regex
    config.parse = parse

    parsed_version = _do_parse(config)

    if parsed_version:
        version_string = format_version(
            parsed_version, version_scheme=version_scheme, local_scheme=local_scheme
        )
        dump_version(
            root=root,
            version=version_string,
            write_to=write_to,
            template=write_to_template,
        )

        return version_string
