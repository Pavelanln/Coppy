# -*- coding: utf-8 -*-
#
# PyTorch documentation build configuration file, created by
# sphinx-quickstart on Fri Dec 23 13:31:47 2016.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
from os import path
# import sys
import pkgutil

# source code directory, relative to this file, for sphinx-autobuild
# sys.path.insert(0, os.path.abspath('../..'))

import torch

try:
    import torchvision  # noqa: F401
except ImportError:
    import warnings
    warnings.warn('unable to load "torchvision" package')

RELEASE = os.environ.get('RELEASE', False)

import pytorch_sphinx_theme

# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#
needs_sphinx = '3.1.2'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.doctest',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinxcontrib.katex',
    'sphinx.ext.autosectionlabel',
    'sphinx_copybutton',
    'sphinx_panels'
]

# build the templated autosummary files
autosummary_generate = True
numpydoc_show_class_members = False

# Theme has bootstrap already
panels_add_bootstrap_css = False

# autosectionlabel throws warnings if section names are duplicated.
# The following tells autosectionlabel to not throw a warning for
# duplicated section names that are in different documents.
autosectionlabel_prefix_document = True

# katex options
#
#

katex_prerender = True

napoleon_use_ivar = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# TODO: document these and remove them from here.

coverage_ignore_functions = [
    # torch
    "typename",
    # torch.autograd
    "register_py_tensor_class_for_device",
    "variable",
    # torch.cuda
    "check_error",
    "cudart",
    "is_bf16_supported",
    # torch.distributed.autograd
    "is_available",
    # torch.distributed.elastic.events
    "construct_and_record_rdzv_event",
    "record_rdzv_event",
    # torch.distributed.elastic.metrics
    "initialize_metrics",
    # torch.distributed.elastic.rendezvous.registry
    "get_rendezvous_handler",
    # torch.distributed.launch
    "launch",
    "main",
    "parse_args",
    # torch.distributed.rpc
    "is_available",
    # torch.distributed.run
    "config_from_args",
    "determine_local_world_size",
    "get_args_parser",
    "get_rdzv_endpoint",
    "get_use_env",
    "main",
    "parse_args",
    "parse_min_max_nnodes",
    "run",
    "run_script_path",
    # torch.distributions.constraints
    "is_dependent",
    # torch.hub
    "import_module",
    # torch.jit
    "export_opnames",
    # torch.jit.unsupported_tensor_ops
    "execWrapper",
    # torch.onnx
    "unregister_custom_op_symbolic",
    # torch.ao.quantization
    "default_eval_fn",
    # torch.ao.quantization.backend_config
    "validate_backend_config_dict",
    # torch.backends
    "disable_global_flags",
    "flags_frozen",
    # torch.distributed.algorithms.ddp_comm_hooks
    "register_ddp_comm_hook",
    # torch.nn
    "factory_kwargs",
    # torch.nn.parallel
    "DistributedDataParallelCPU",
    # torch.utils
    "set_module",
    # torch.utils.model_dump
    "burn_in_info",
    "get_info_and_burn_skeleton",
    "get_inline_skeleton",
    "get_model_info",
    "get_storage_info",
    "hierarchical_pickle",
]

coverage_ignore_classes = [
    # torch
    "FatalError",
    "QUInt2x4Storage",
    "Size",
    "Storage",
    "Stream",
    "Tensor",
    "finfo",
    "iinfo",
    "qscheme",
    "AggregationType",
    "AliasDb",
    "AnyType",
    "Argument",
    "ArgumentSpec",
    "BenchmarkConfig",
    "BenchmarkExecutionStats",
    "Block",
    "BoolType",
    "BufferDict",
    "CallStack",
    "Capsule",
    "ClassType",
    "Code",
    "CompleteArgumentSpec",
    "ComplexType",
    "ConcreteModuleType",
    "ConcreteModuleTypeBuilder",
    "DeepCopyMemoTable",
    "DeserializationStorageContext",
    "DeviceObjType",
    "DictType",
    "EnumType",
    "ExecutionPlan",
    "FileCheck",
    "FloatType",
    "FunctionSchema",
    "Gradient",
    "Graph",
    "GraphExecutorState",
    "IODescriptor",
    "InferredType",
    "IntType",
    "InterfaceType",
    "ListType",
    "LockingLogger",
    "MobileOptimizerType",
    "ModuleDict",
    "Node",
    "NoneType",
    "NoopLogger",
    "NumberType",
    "OperatorInfo",
    "OptionalType",
    "ParameterDict",
    "PyObjectType",
    "PyTorchFileReader",
    "PyTorchFileWriter",
    "RRefType",
    "ScriptClass",
    "ScriptClassFunction",
    "ScriptDict",
    "ScriptDictIterator",
    "ScriptDictKeyIterator",
    "ScriptList",
    "ScriptListIterator",
    "ScriptMethod",
    "ScriptModule",
    "ScriptModuleSerializer",
    "ScriptObject",
    "ScriptObjectProperty",
    "SerializationStorageContext",
    "StaticModule",
    "StringType",
    "SymIntType",
    "ThroughputBenchmark",
    "TracingState",
    "TupleType",
    "Type",
    "UnionType",
    "Use",
    "Value",
    # torch.cuda
    "BFloat16Storage",
    "BFloat16Tensor",
    "BoolStorage",
    "BoolTensor",
    "ByteStorage",
    "ByteTensor",
    "CharStorage",
    "CharTensor",
    "ComplexDoubleStorage",
    "ComplexFloatStorage",
    "CudaError",
    "DeferredCudaCallError",
    "DoubleStorage",
    "DoubleTensor",
    "FloatStorage",
    "FloatTensor",
    "HalfStorage",
    "HalfTensor",
    "IntStorage",
    "IntTensor",
    "LongStorage",
    "LongTensor",
    "ShortStorage",
    "ShortTensor",
    "cudaStatus",
    # torch.distributed.elastic.multiprocessing.errors
    "ChildFailedError",
    "ProcessFailure",
    # torch.distributions.constraints
    "cat",
    "greater_than",
    "greater_than_eq",
    "half_open_interval",
    "independent",
    "integer_interval",
    "interval",
    "less_than",
    "multinomial",
    "stack",
    # torch.distributions.transforms
    "AffineTransform",
    "CatTransform",
    "ComposeTransform",
    "CorrCholeskyTransform",
    "CumulativeDistributionTransform",
    "ExpTransform",
    "IndependentTransform",
    "PowerTransform",
    "ReshapeTransform",
    "SigmoidTransform",
    "SoftmaxTransform",
    "SoftplusTransform",
    "StackTransform",
    "StickBreakingTransform",
    "TanhTransform",
    "Transform",
    # torch.jit
    "CompilationUnit",
    "Error",
    "Future",
    "ScriptFunction",
    # torch.onnx
    "CheckerError",
    "ExportTypes",
    # torch.backends
    "ContextProp",
    "PropModule",
    # torch.backends.cuda
    "cuBLASModule",
    "cuFFTPlanCache",
    "cuFFTPlanCacheAttrContextProp",
    "cuFFTPlanCacheManager",
    # torch.distributed.algorithms.ddp_comm_hooks
    "DDPCommHookType",
    # torch.jit.mobile
    "LiteScriptModule",
    # torch.nn.quantized.modules
    "DeQuantize",
    "Quantize",
    # torch.utils.backcompat
    "Warning",
]

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
# source_suffix = ['.rst', '.md']
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'PyTorch'
copyright = '2022, PyTorch Contributors'
author = 'PyTorch Contributors'
torch_version = str(torch.__version__)

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
# TODO: change to [:2] at v1.0
version = 'master (' + torch_version + ' )'
# The full version, including alpha/beta/rc tags.
# TODO: verify this works as expected
release = 'master'

# Customized html_title here.
# Default is " ".join(project, release, "documentation") if not set
if RELEASE:
    # Turn 1.11.0aHASH into 1.11
    # Note: the release candidates should no longer have the aHASH suffix, but in any
    # case we wish to leave only major.minor, even for rc builds.
    version = '.'.join(torch_version.split('.')[:2])
    html_title = " ".join((project, version, "documentation"))
    release = version

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = None

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This patterns also effect to html_static_path and html_extra_path
exclude_patterns = []

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = True

# Disable docstring inheritance
autodoc_inherit_docstrings = False

# Disable displaying type annotations, these can be very verbose
autodoc_typehints = 'none'

# Enable overriding of function signatures in the first line of the docstring.
autodoc_docstring_signature = True

# -- katex javascript in header
#
#    def setup(app):
#    app.add_javascript("https://cdn.jsdelivr.net/npm/katex@0.10.0-beta/dist/katex.min.js")


# -- Options for HTML output ----------------------------------------------
#
# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
#
#

html_theme = 'pytorch_sphinx_theme'
html_theme_path = [pytorch_sphinx_theme.get_html_theme_path()]

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.

html_theme_options = {
    'pytorch_project': 'docs',
    'canonical_url': 'https://pytorch.org/docs/stable/',
    'collapse_navigation': False,
    'display_version': True,
    'logo_only': True,
    'analytics_id': 'UA-117752657-2',
}

html_logo = '_static/img/pytorch-logo-dark-unstable.png'
if RELEASE:
    html_logo = '_static/img/pytorch-logo-dark.svg'


# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

html_css_files = [
    'css/jit.css',
]

from sphinx.ext.coverage import CoverageBuilder

def coverage_post_process(app, exception):
    if exception is not None:
        return

    # Only run this test for the coverage build
    if not isinstance(app.builder, CoverageBuilder):
        return

    if not torch.distributed.is_available():
        raise RuntimeError("The coverage tool cannot run with a version "
                           "of PyTorch that was built with USE_DISTRIBUTED=0 "
                           "as this module's API changes.")

    # These are all the modules that have "automodule" in an rst file
    # These modules are the ones for which coverage is checked
    # Here, we make sure that no module is missing from that list
    modules = app.env.domaindata['py']['modules']

    # We go through all the torch submodules and make sure they are
    # properly tested
    missing = set()

    def is_not_internal(modname):
        split_name = modname.split(".")
        for name in split_name:
            if name[0] == "_":
                return False
        return True

    # The walk function does not return the top module
    if "torch" not in modules:
        missing.add("torch")

    for _, modname, ispkg in pkgutil.walk_packages(path=torch.__path__,
                                                   prefix=torch.__name__ + '.'):
        if ispkg and is_not_internal(modname):
            if modname not in modules:
                missing.add(modname)

    output = []

    if missing:
        mods = ", ".join(missing)
        output.append(f"\nYou added the following module(s) to the PyTorch namespace '{mods}' "
                      "but they have no corresponding entry in a doc .rst file. You should "
                      "either make sure that the .rst file that contains the module's documentation "
                      "properly contains either '.. automodule:: mod_name' (if you do not want "
                      "the paragraph added by the automodule, you can simply use '.. py:module:: mod_name') "
                      " or make the module private (by appending an '_' at the beginning of its name).")

    # The output file is hard-coded by the coverage tool
    # Our CI is setup to fail if any line is added to this file
    output_file = path.join(app.outdir, 'python.txt')

    if output:
        with open(output_file, "a") as f:
            for o in output:
                f.write(o)

# Called automatically by Sphinx, making this `conf.py` an "extension".
def setup(app):
    # NOTE: in Sphinx 1.8+ `html_css_files` is an official configuration value
    # and can be moved outside of this function (and the setup(app) function
    # can be deleted).
    html_css_files = [
        'https://cdn.jsdelivr.net/npm/katex@0.10.0-beta/dist/katex.min.css'
    ]

    # In Sphinx 1.8 it was renamed to `add_css_file`, 1.7 and prior it is
    # `add_stylesheet` (deprecated in 1.8).
    add_css = getattr(app, 'add_css_file', app.add_stylesheet)
    for css_file in html_css_files:
        add_css(css_file)

    app.connect("build-finished", coverage_post_process)

# From PyTorch 1.5, we now use autogenerated files to document classes and
# functions. This breaks older references since
# https://pytorch.org/docs/stable/torch.html#torch.flip
# moved to
# https://pytorch.org/docs/stable/generated/torch.flip.html
# which breaks older links from blog posts, stack overflow answers and more.
# To mitigate that, we add an id="torch.flip" in an appropriated place
# in torch.html by overriding the visit_reference method of html writers.
# Someday this can be removed, once the old links fade away

from sphinx.writers import html, html5

def replace(Klass):
    old_call = Klass.visit_reference

    def visit_reference(self, node):
        if 'refuri' in node and 'generated' in node.get('refuri'):
            ref = node.get('refuri')
            ref_anchor = ref.split('#')
            if len(ref_anchor) > 1:
                # Only add the id if the node href and the text match,
                # i.e. the href is "torch.flip#torch.flip" and the content is
                # "torch.flip" or "flip" since that is a signal the node refers
                # to autogenerated content
                anchor = ref_anchor[1]
                txt = node.parent.astext()
                if txt == anchor or txt == anchor.split('.')[-1]:
                    self.body.append('<p id="{}"/>'.format(ref_anchor[1]))
        return old_call(self, node)
    Klass.visit_reference = visit_reference

replace(html.HTMLTranslator)
replace(html5.HTML5Translator)

# -- Options for HTMLHelp output ------------------------------------------

# Output file base name for HTML help builder.
htmlhelp_basename = 'PyTorchdoc'


# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    #
    # 'papersize': 'letterpaper',

    # The font size ('10pt', '11pt' or '12pt').
    #
    # 'pointsize': '10pt',

    # Additional stuff for the LaTeX preamble.
    #
    # 'preamble': '',

    # Latex figure (float) alignment
    #
    # 'figure_align': 'htbp',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    (master_doc, 'pytorch.tex', 'PyTorch Documentation',
     'Torch Contributors', 'manual'),
]


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    (master_doc, 'PyTorch', 'PyTorch Documentation',
     [author], 1)
]


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (master_doc, 'PyTorch', 'PyTorch Documentation',
     author, 'PyTorch', 'One line description of project.',
     'Miscellaneous'),
]


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'numpy': ('https://numpy.org/doc/stable', None),
}

# -- A patch that prevents Sphinx from cross-referencing ivar tags -------
# See http://stackoverflow.com/a/41184353/3343043

from docutils import nodes
from sphinx.util.docfields import TypedField
from sphinx import addnodes
import sphinx.ext.doctest

# Without this, doctest adds any example with a `>>>` as a test
doctest_test_doctest_blocks = ''
doctest_default_flags = sphinx.ext.doctest.doctest.ELLIPSIS
doctest_global_setup = '''
import torch
try:
    import torchvision
except ImportError:
    torchvision = None
'''


def patched_make_field(self, types, domain, items, **kw):
    # `kw` catches `env=None` needed for newer sphinx while maintaining
    #  backwards compatibility when passed along further down!

    # type: (List, unicode, Tuple) -> nodes.field
    def handle_item(fieldarg, content):
        par = nodes.paragraph()
        par += addnodes.literal_strong('', fieldarg)  # Patch: this line added
        # par.extend(self.make_xrefs(self.rolename, domain, fieldarg,
        #                           addnodes.literal_strong))
        if fieldarg in types:
            par += nodes.Text(' (')
            # NOTE: using .pop() here to prevent a single type node to be
            # inserted twice into the doctree, which leads to
            # inconsistencies later when references are resolved
            fieldtype = types.pop(fieldarg)
            if len(fieldtype) == 1 and isinstance(fieldtype[0], nodes.Text):
                typename = u''.join(n.astext() for n in fieldtype)
                typename = typename.replace('int', 'python:int')
                typename = typename.replace('long', 'python:long')
                typename = typename.replace('float', 'python:float')
                typename = typename.replace('bool', 'python:bool')
                typename = typename.replace('type', 'python:type')
                par.extend(self.make_xrefs(self.typerolename, domain, typename,
                                           addnodes.literal_emphasis, **kw))
            else:
                par += fieldtype
            par += nodes.Text(')')
        par += nodes.Text(' -- ')
        par += content
        return par

    fieldname = nodes.field_name('', self.label)
    if len(items) == 1 and self.can_collapse:
        fieldarg, content = items[0]
        bodynode = handle_item(fieldarg, content)
    else:
        bodynode = self.list_type()
        for fieldarg, content in items:
            bodynode += nodes.list_item('', handle_item(fieldarg, content))
    fieldbody = nodes.field_body('', bodynode)
    return nodes.field('', fieldname, fieldbody)

TypedField.make_field = patched_make_field

copybutton_prompt_text = r'>>> |\.\.\. '
copybutton_prompt_is_regexp = True
