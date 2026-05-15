"""JSX Builder for Sphinx - generates JSX-compatible HTML with React components."""

import logging
import os
import re
import types
from os import path
from pathlib import Path
from typing import IO, TYPE_CHECKING , Any, Protocol

import json

from collections import UserString

from sphinx.application import ENV_PICKLE_FILENAME, Sphinx
from sphinx.builders.html import BuildInfo, StandaloneHTMLBuilder
from sphinx.util import logging as sphinx_logging
from sphinx.util.osutil import SEP, copyfile, ensuredir, os_path
#from sphinxcontrib.serializinghtml import SerializingHTMLBuilder, jsonimpl

from jsx_builder import jsxfileimpl

from jsx_builder.translator import JSXTranslator

class JsxOutputImplementation(Protocol):
        def createPage(self, obj: Any, *args: Any, **kwds: Any) -> None: ...
        def createAsset(self, obj: Any, *args: Any, **kwds: Any) -> None: ...
        def createSection(self, obj: Any, *args: Any, **kwds: Any) -> None: ...
        def finalize(self, obj: Any, *args: Any, **kwds: Any) -> None: ...
        def dump(self, obj: Any, file: Any, *args: Any, **kwds: Any) -> None: ...


logger = sphinx_logging.getLogger(__name__)

LAST_BUILD_FILENAME = 'last_build'

class JSXBuilder(StandaloneHTMLBuilder):
    """Abstract JSX Builder for Sphinx - generates JSX-compatible HTML with React components."""

    name = "jsx"
    format = "html"  # Generates HTML with JSX-compatible React components
    file_suffix = ".html"
    links_suffix = None

    implementation: JsxOutputImplementation

    implementation_dumps_unicode = False

    # Use JSX translator to generate JSX components directly
    default_translator_class = JSXTranslator
    image_extensions = {
        '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.bmp', '.ico', '.avif', '.tif', '.tiff'
    }

    def init(self) -> None:
        self.build_info = BuildInfo(self.config, self.tags)
        self.imagedir = '_images'
        self.current_docname = ''
        self.theme = None  # type: ignore[assignment] # no theme necessary
        self.templates = None  # no template bridge necessary
        self.init_templates()
        self.init_highlighter()
        self.init_css_files()
        self.init_js_files()
        self.use_index = self.get_builder_config('use_index', 'html')
        
        # Self-closing HTML tags that need to be converted to JSX syntax
        self.self_closing_tags = {
            'img', 'br', 'hr', 'input', 'meta', 'link', 'area', 'base', 
            'col', 'embed', 'source', 'track', 'wbr'
        }

    def get_target_uri(self, docname: str, typ: str | None = None) -> str:
        if docname == 'index':
            return ''
        if docname.endswith(SEP + 'index'):
            return docname[:-5]  # up to sep
        return docname + SEP
    
    def dump_context(self, context: dict[str, Any], filename: str | os.PathLike[str]) -> None:
        context = context.copy()
        if 'css_files' in context:
            context['css_files'] = [css.filename for css in context['css_files']]
        if 'script_files' in context:
            context['script_files'] = [js.filename for js in context['script_files']]
        if self.implementation_dumps_unicode:
            with open(filename, 'w', encoding='utf-8') as ft:
                self.implementation.dump(context, ft, *self.additional_dump_args)
        else:
            with open(filename, 'wb') as fb:
                self.implementation.dump(context, fb, *self.additional_dump_args)

    def handle_page(self, pagename: str, ctx: dict[str, Any], templatename: str = 'page.html',
                    outfilename: str | None = None, event_arg: Any = None) -> None:
        ctx['current_page_name'] = pagename
        ctx.setdefault('pathto', lambda p: p)
        #self.add_sidebars(pagename, ctx)

        if not outfilename:
            outfilename = path.join(self.outdir,
                                    os_path(pagename) + self.out_suffix)

        self.app.emit('html-page-context', pagename, templatename, ctx, event_arg)

        # Add section tree to context if available from the translator
        if hasattr(self, 'docwriter') and hasattr(self.docwriter, 'visitor'):
            visitor = self.docwriter.visitor
            if hasattr(visitor, 'section_list'):
                ctx['section_list'] = visitor.section_list
            if hasattr(visitor, 'section_tree'):
                ctx['section_tree'] = visitor.section_tree

        # make context object serializable
        for key in list(ctx):
            if isinstance(ctx[key], types.FunctionType):
                del ctx[key]

        ensuredir(path.dirname(outfilename))
        self.dump_context(ctx, outfilename)

        django_cfg = getattr(self.config, 'django', None)
        DocId = django_cfg.get('docId', None) if isinstance(django_cfg, dict) else None

        self.implementation.createPage(obj=ctx, docId=DocId, outDir=self.outdir)

        if ctx.get('sourcename'):
            source_name = path.join(self.outdir, '_sources',
                                    os_path(ctx['sourcename']))
            ensuredir(path.dirname(source_name))
            copyfile(self.env.doc2path(pagename), source_name)


    def handle_finish(self) -> None:

        self.globalcontext['toc_pages'] = self._build_toc_pages()

        outfilename = path.join(self.outdir, self.globalcontext_filename)
        self.dump_context(self.globalcontext, outfilename)

        django_cfg = getattr(self.config, 'django', None)
        DocId = django_cfg.get('docId', None) if isinstance(django_cfg, dict) else None

                # make context object serializable
        for key in list(self.globalcontext):
            if isinstance(self.globalcontext[key], types.FunctionType):
                del self.globalcontext[key]

        self.implementation.finalize(obj=self.globalcontext, outDir=self.outdir, docId=DocId)

        # super here to dump the search index
        super().handle_finish()

        # Notify implementation about all static image assets copied by Sphinx.
        # At this point _images/_static already exist in outdir.
        static_image_assets = self._collect_static_images()
        for asset in static_image_assets:
            self.implementation.createAsset(obj=asset, outDir=self.outdir, docId=DocId)

        # copy the environment file from the doctree dir to the output dir
        # as needed by the web app
        copyfile(path.join(self.doctreedir, ENV_PICKLE_FILENAME),
                 path.join(self.outdir, ENV_PICKLE_FILENAME))

        # touch 'last build' file, used by the web application to determine
        # when to reload its environment and clear the cache
        open(path.join(self.outdir, LAST_BUILD_FILENAME), 'w').close()

                
        logger.info("JSX HTML build complete!")

    def _build_toc_pages(self) -> list[str]:
        """Build a deterministic page order from Sphinx toctree relations."""
        master_doc = getattr(self.config, 'master_doc', None)
        toctree = getattr(self.env, 'toctree_includes', {})
        found_docs = sorted(getattr(self.env, 'found_docs', []))

        ordered: list[str] = []
        visited: set[str] = set()

        def walk(docname: str) -> None:
            if docname in visited:
                return
            visited.add(docname)
            ordered.append(docname)
            for child in toctree.get(docname, []):
                walk(child)

        if master_doc:
            walk(master_doc)

        for docname in found_docs:
            if docname not in visited:
                ordered.append(docname)

        return ordered

    def _collect_static_images(self) -> list[dict[str, str]]:
        """Collect static image assets from standard Sphinx output folders."""
        assets: list[dict[str, str]] = []
        static_dirs = [
            Path(self.outdir) / self.imagedir,
            Path(self.outdir) / '_static',
        ]

        for base_dir in static_dirs:
            if not base_dir.exists():
                continue

            for file_path in base_dir.rglob('*'):
                if not file_path.is_file():
                    continue

                if file_path.suffix.lower() not in self.image_extensions:
                    continue

                rel_path = file_path.relative_to(self.outdir).as_posix()
                assets.append({
                    'path': rel_path,
                    'filename': file_path.name,
                    'absolute_path': str(file_path),
                })

        return assets

    def _apply_jsx_attribute_fixes(self, html_file: Path):
        """Apply minimal JSX attribute fixes to HTML file."""
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple regex replacements for JSX compatibility
            content = re.sub(r'\bclass=', 'className=', content)
            content = re.sub(r'\bfor=', 'htmlFor=', content) 
            content = re.sub(r'\btabindex=', 'tabIndex=', content)
            content = re.sub(r'\breadonly=', 'readOnly=', content)
            content = re.sub(r'\bmaxlength=', 'maxLength=', content)
            content = re.sub(r'\browspan=', 'rowSpan=', content)
            content = re.sub(r'\bcolspan=', 'colSpan=', content)
            
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(content)
                
        except Exception as e:
            logger.warning(f"Failed to apply JSX fixes to {html_file}: {e}")




class SphinxJSONEncoder(json.JSONEncoder):
    """JSONEncoder subclass that forces translation proxies."""
    def default(self, obj: Any) -> str:
        # Handle Sphinx-specific helper objects (_JavaScript, translation proxies, etc.)
        if isinstance(obj, UserString):
            return str(obj)
        if obj.__class__.__name__ == '_JavaScript':
            return str(obj)
        try:
            return super().default(obj)
        except TypeError:
            # Fallback: stringify any other non-serializable object
            return str(obj)
    
class JsxFileOutputImplementation(JsxOutputImplementation):
    """JSON serializer implementation wrapper."""
    def dump(self, obj: Any, file: IO[str] | IO[bytes], *args: Any, **kwds: Any) -> None:
        kwds['cls'] = SphinxJSONEncoder
        json.dump(obj, file, *args, **kwds)
    
    def createPage(self, obj: Any, *args: Any, **kwds: Any) -> None:
        if kwds["outDir"]:

            if isinstance(obj, dict) and "current_page_name" in obj and "body" in obj:
                with open(f"{kwds['outDir']}/{obj['current_page_name']}.html", "w", encoding="utf-8") as f:
                    f.write(obj["body"])
    def createAsset(self, obj: Any, *args: Any, **kwds: Any) -> None:
        pass  # Implement asset creation if needed
    def createSection(self, obj: Any, *args: Any, **kwds: Any) -> None:
        pass  # Implement section creation if needed
    def finalize(self, obj: Any, *args: Any, **kwds: Any) -> None:
        pass  # Implement finalization if needed


class JSONJSXBuilder(JSXBuilder):
    """
    A builder that dumps the generated JSX HTML into JSON files.
    """
    name = 'jjson'
    epilog = 'You can now process the JSON files in %(outdir)s.'

    implementation = JsxFileOutputImplementation()
    implementation_dumps_unicode = True
    additional_dump_args: tuple[Any] = ()
    out_suffix = '.fjson'
    globalcontext_filename = 'globalcontext.json'
    searchindex_filename = 'searchindex.json'