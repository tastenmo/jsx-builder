"""JSX-specific HTML5 translator for Sphinx JSX builder."""

import logging
import re
import hashlib
from typing import Any

from docutils import nodes
from docutils.nodes import Element
from sphinx.writers.html5 import HTML5Translator

logger = logging.getLogger(__name__)


class JSXTranslator(HTML5Translator):
    """JSX-specific HTML5 translator that outputs JSX-compatible HTML."""

    def __init__(self, *args, **kwargs):
        """Initialize the JSX translator."""
        super().__init__(*args, **kwargs)

        self.special_characters.update({ord('{'): '&#123;', ord('}'): '&#125;'})

        # Track JSX components used for import generation
        self.jsx_components_used = set()
        
        # Section tree tracking
        self.section_list = []
        self.section_tree = []
        self._section_stack = []
        self._section_order_counter = 0

    def _make_toc_node(self, section_node: dict[str, Any]) -> dict[str, Any]:
        """Create a compact TOC node representation from a section node."""
        return {
            'id': section_node.get('id', ''),
            'title': section_node.get('title', ''),
            'level': section_node.get('level', 1),
            'hash': section_node.get('hash', ''),
            'source': section_node.get('source', ''),
            'startline': section_node.get('startline', 0),
            'endline': section_node.get('endline', 0),
            'order_index': section_node.get('order_index', 0),
            'children': section_node.get('children', []),
        }

    def visit_section(self, node: Element) -> None:
        """Handle section start - add JSX Section component if needed."""
        self.jsx_components_used.add('Section')
        self.section_level += 1
        attrs = []
        
        # Handle IDs
        ids = node.get('ids', [])
        id_str = ' '.join(ids) if ids else ''
        if id_str:
            attrs.append(f'id="{id_str}"')
        
        attrs.append(f'level="{self.section_level}"')

        if node.source:
            attrs.append(f'source="{node.source}"')
        
        if node.line:
            attrs.append(f'line="{node.line}"')
        
        # Add section number if available
        secnumber = self.get_secnumber(node)
        secnumber_str = ''
        if secnumber:
            secnumber_str = '.'.join(map(str, secnumber))
            attrs.append(f'secnumber="{secnumber_str}"')
        
        # Get the title text if available
        title_text = ''
        for child in node.children:
            if isinstance(child, nodes.title):
                title_text = child.astext()
                break
        
        # Generate hash for the section based on structure and content
        content_parts = [f"title:{title_text}"]
        for child in node.children:
            # Exclude nested sections from the hash content to avoid dependency on children
            if not isinstance(child, nodes.section):
                # Create a signature including type, attributes, and content
                # Sort attributes for deterministic hashing
                child_attrs = sorted(
                    (k, str(v)) for k, v in child.attributes.items() 
                    if k not in ('ids', 'names', 'dupnames', 'backrefs', 'source', 'line')
                )
                sig = f"[{child.tagname}]{child_attrs}:{child.astext()}"
                content_parts.append(sig)
        
        hash_content = "\n".join(content_parts)
        section_hash = hashlib.sha1(hash_content.encode('utf-8')).hexdigest()
        attrs.append(f'hash="{section_hash}"')

        # Build tree node
        section_node = {
            'id': id_str,
            'title': title_text,
            'level': self.section_level,
            'secnumber': secnumber_str,
            'hash': section_hash,
            'source': node.source,
            'startline': node.line,
            'order_index': self._section_order_counter,
            'children': []
        }
        self._section_order_counter += 1

        # Push to stack
        self._section_stack.append(section_node)
        
        if title_text:
            attrs.append(f'title="{self._escape_attr(title_text)}"')

        section_node['start_index'] = len(self.body)
        self.body.append(f'<Section {" ".join(attrs)}>')
        self.context.append('</Section>')

    def depart_section(self, node: Element) -> None:
        """Handle section end - close JSX Section component."""
        self.jsx_components_used.add('SectionRef')
        self.section_level -= 1
        self.body.append(self.context.pop())

        
        # Capture section body content
        if self._section_stack:
            section_node = self._section_stack.pop()
            if 'start_index' in section_node:
                start_idx = section_node['start_index']
                # Capture the full content including wrapper
                section_node['body'] = "".join(self.body[start_idx:])
                if node.line:
                    section_node['endline'] = node.line

                del section_node['start_index']
                
                # Remove content from main body and replace with SectionRef
                del self.body[start_idx:]
                self.body.append(f'<SectionRef hash="{section_node["hash"]}" />')

                if self._section_stack:
                    parent_node = self._section_stack[-1]
                    section_node['parent_hash'] = parent_node.get('hash', '')
                    parent_node['children'].append(self._make_toc_node(section_node))
                else:
                    section_node['parent_hash'] = ''
                    self.section_tree.append(self._make_toc_node(section_node))
                
                # Add to flat list
                self.section_list.append(section_node)
        
    def visit_table(self, node: Element) -> None:
        """Handle table element - use JSX Table component."""
        self.jsx_components_used.add('Table')
        # Extract table classes and attributes
        classes = node.get('classes', [])
        # Build JSX attributes
        attrs = []
        if classes:
            class_str = ' '.join(classes)
            attrs.append(f'className="{class_str}"')
        # Add other table attributes (always quote values for JSX)
        for attr in node.attributes:
            if attr not in ['classes', 'ids']:
                value = node.attributes[attr]
                jsx_attr = self._html_attr_to_jsx(attr)
                attrs.append(f'{jsx_attr}="{value}"')
        attr_string = ' ' + ' '.join(attrs) if attrs else ''
        self.body.append(f'<Table{attr_string}>')
        self.context.append('</Table>')

    def depart_table(self, node: Element) -> None:
        """Close table element."""
        self.body.append(self.context.pop())

    def visit_thead(self, node: Element) -> None:
        """Handle table head - use JSX TableHead component."""
        self.jsx_components_used.add('TableHead')
        self.body.append('<TableHead>')
        self.context.append('</TableHead>')

    def depart_thead(self, node: Element) -> None:
        """Close table head element."""
        self.body.append(self.context.pop())

    def visit_tbody(self, node: Element) -> None:
        """Handle table body - use JSX TableBody component."""
        self.jsx_components_used.add('TableBody')
        self.body.append('<TableBody>')
        self.context.append('</TableBody>')

    def depart_tbody(self, node: Element) -> None:
        """Close table body element."""
        self.body.append(self.context.pop())

    def visit_tfoot(self, node: Element) -> None:
        """Handle table foot - use JSX TableFoot component."""
        self.jsx_components_used.add('TableFoot')
        self.body.append('<TableFoot>')
        self.context.append('</TableFoot>')

    def depart_tfoot(self, node: Element) -> None:
        """Close table foot element."""
        self.body.append(self.context.pop())

    def visit_row(self, node: Element) -> None:
        """Handle table row - use JSX TableRow component."""
        self.jsx_components_used.add('TableRow')
        
        # Handle row attributes
        attrs = []
        classes = node.get('classes', [])
        if classes:
            class_str = ' '.join(classes)
            attrs.append(f'className="{class_str}"')
        
        attr_string = ' ' + ' '.join(attrs) if attrs else ''
        
        self.body.append(f'<TableRow{attr_string}>')
        self.context.append('</TableRow>')

    def depart_row(self, node: Element) -> None:
        """Close table row element."""
        self.body.append(self.context.pop())

    def visit_entry(self, node: Element) -> None:
        """Handle table cell - use JSX TableCell component."""
        self.jsx_components_used.add('TableCell')
        
        # Determine if header or data cell
        is_header = node.parent.parent.tagname == 'thead'
        
        # Handle cell attributes
        attrs = []
        classes = node.get('classes', [])
        if is_header:
            classes.append('header-cell')
        
        if classes:
            class_str = ' '.join(classes)
            attrs.append(f'className="{class_str}"')
        
        # Handle colspan and rowspan (always quote values for JSX)
        if node.get('morecols'):
            colspan = node['morecols'] + 1
            attrs.append(f'colSpan="{colspan}"')
        
        if node.get('morerows'):
            rowspan = node['morerows'] + 1
            attrs.append(f'rowSpan="{rowspan}"')
        
        # Mark as header cell (always quote boolean for JSX)
        if is_header:
            attrs.append('isHeader="true"')

        if node.line:
            attrs.append(f'line="{node.line}"')
        
        attr_string = ' ' + ' '.join(attrs) if attrs else ''
        
        self.body.append(f'<TableCell{attr_string}>')
        self.context.append('</TableCell>')

    def depart_entry(self, node: Element) -> None:
        """Close table cell element."""
        self.body.append(self.context.pop())

    def _build_image_attrs(self, node: Element, caption: str = '') -> list[str]:
        """Build JSX attributes for Image component from docutils image node."""
        attrs = []

        uri = node.get('uri', '')
        if uri:
            attrs.append(f'src="{self._escape_attr(str(uri))}"')

        alt = node.get('alt') or caption
        if alt:
            attrs.append(f'alt="{self._escape_attr(str(alt))}"')

        if caption:
            attrs.append(f'caption="{self._escape_attr(str(caption))}"')

        classes = node.get('classes', [])
        if classes:
            attrs.append(f'className="{self._escape_attr(" ".join(classes))}"')

        for attr_name in ('width', 'height', 'align', 'scale'):
            value = node.get(attr_name)
            if value not in (None, ''):
                jsx_attr = self._html_attr_to_jsx(attr_name)
                attrs.append(f'{jsx_attr}="{self._escape_attr(str(value))}"')

        if node.source:
            attrs.append(f'source="{self._escape_attr(str(node.source))}"')
        if node.line:
            attrs.append(f'line="{node.line}"')

        return attrs

    def visit_image(self, node: Element) -> None:
        """Translate docutils image node to JSX Image component."""
        self.jsx_components_used.add('Image')
        attrs = self._build_image_attrs(node)
        attr_string = ' ' + ' '.join(attrs) if attrs else ''
        self.body.append(f'<Image{attr_string} />')
        raise nodes.SkipNode

    def visit_figure(self, node: Element) -> None:
        """Translate docutils figure node to a JSX Image component."""
        self.jsx_components_used.add('Image')

        image_node = next((child for child in node.children if isinstance(child, nodes.image)), None)
        if image_node is None:
            return

        caption_node = next((child for child in node.children if isinstance(child, nodes.caption)), None)
        caption = caption_node.astext() if caption_node else ''

        attrs = self._build_image_attrs(image_node, caption=caption)

        figure_classes = node.get('classes', [])
        if figure_classes:
            class_attr = next((attr for attr in attrs if attr.startswith('className=')), None)
            if class_attr:
                attrs.remove(class_attr)
                existing_classes = class_attr.split('="', 1)[1].rstrip('"')
                merged_classes = ' '.join(
                    part for part in (existing_classes, ' '.join(figure_classes)) if part
                )
                attrs.append(f'className="{self._escape_attr(merged_classes)}"')
            else:
                attrs.append(f'className="{self._escape_attr(" ".join(figure_classes))}"')

        if node.source:
            attrs.append(f'figureSource="{self._escape_attr(str(node.source))}"')
        if node.line:
            attrs.append(f'figureLine="{node.line}"')

        attr_string = ' ' + ' '.join(attrs) if attrs else ''
        self.body.append(f'<Image{attr_string} />')
        raise nodes.SkipNode

    def visit_reference(self, node: Element) -> None:
        """Handle reference (link) - use JSX Link component for internal links."""
        # Check if this is an internal reference
        if node.get('internal') or 'refuri' not in node:
            self.jsx_components_used.add('Link')
            
            # Build Link component attributes
            attrs = []
            
            # Handle href
            href = node.get('refuri') or f"#{node.get('refid', '')}"
            attrs.append(f'to="{href}"')
            
            # Handle classes
            classes = node.get('classes', [])
            if classes:
                class_str = ' '.join(classes)
                attrs.append(f'className="{class_str}"')
            
            attr_string = ' ' + ' '.join(attrs) if attrs else ''
            
            self.body.append(f'<Link{attr_string}>')
            self.context.append('</Link>')
        else:
            # External link - use regular anchor tag
            super().visit_reference(node)

    def depart_reference(self, node: Element) -> None:
        """Close reference element."""
        if node.get('internal') or 'refuri' not in node:
            self.body.append(self.context.pop())
        else:
            super().depart_reference(node)

    def visit_literal_block(self, node: Element) -> None:
        """Handle code blocks - use JSX CodeBlock component."""
        self.jsx_components_used.add('CodeBlock')
        
        # Extract language and other attributes
        attrs = []
        
        # Handle language
        language = node.get('language', '')
        if language:
            attrs.append(f'language="{language}"')
        
        # Handle classes
        classes = node.get('classes', [])
        if classes:
            class_str = ' '.join(classes)
            attrs.append(f'className="{class_str}"')
        #if node.rawsource == node.astext():
            # Escape double quotes in text
        #    text = node.astext().replace('"', '\"')
        #    attrs.append(f'text="{text}"')
        
        attr_string = ' ' + ' '.join(attrs) if attrs else ''
        
        self.body.append(f'<CodeBlock{attr_string}>')
        self.context.append('</CodeBlock>')
        #raise nodes.SkipNode  # Skip further processing since we handled content here

    def depart_literal_block(self, node: Element) -> None:
        """Close code block element."""
        self.body.append(self.context.pop())

    def visit_admonition(self, node: Element, name: str = '') -> None:
        """Handle admonitions - use JSX Note component."""
        self.jsx_components_used.add('Note')
        
        # Determine admonition type
        admonition_type = name or 'note'  # Use provided name or default
        classes = node.get('classes', [])
        
        # Override with class if found
        for cls in classes:
            if cls in ['note', 'warning', 'tip', 'important', 'caution', 'danger', 'error']:
                admonition_type = cls
                break
        
        # Build Note component attributes
        attrs = [f'type="{admonition_type}"']
        
        if classes:
            class_str = ' '.join(classes)
            attrs.append(f'className="{class_str}"')
        
        attr_string = ' ' + ' '.join(attrs)
        
        self.body.append(f'<Note{attr_string}>')
        self.context.append('</Note>')

    def depart_admonition(self, node: Element, name: str = '') -> None:
        """Close admonition element."""
        self.body.append(self.context.pop())

    def visit_note(self, node: Element) -> None:
        """Handle note admonition."""
        self.visit_admonition(node, 'note')

    def depart_note(self, node: Element) -> None:
        """Close note admonition."""
        self.depart_admonition(node, 'note')

    def visit_warning(self, node: Element) -> None:
        """Handle warning admonition."""
        self.visit_admonition(node, 'warning')

    def depart_warning(self, node: Element) -> None:
        """Close warning admonition."""
        self.depart_admonition(node, 'warning')

    def visit_tip(self, node: Element) -> None:
        """Handle tip admonition."""
        self.visit_admonition(node, 'tip')

    def depart_tip(self, node: Element) -> None:
        """Close tip admonition."""
        self.depart_admonition(node, 'tip')

    def visit_important(self, node: Element) -> None:
        """Handle important admonition."""
        self.visit_admonition(node, 'important')

    def depart_important(self, node: Element) -> None:
        """Close important admonition."""
        self.depart_admonition(node, 'important')

    def visit_error(self, node: Element) -> None:
        """Handle error admonition."""
        self.visit_admonition(node, 'error')

    def depart_error(self, node: Element) -> None:
        """Close error admonition."""
        self.depart_admonition(node, 'error')

    def _html_attr_to_jsx(self, attr_name: str) -> str:
        """Convert HTML attribute names to JSX format."""
        conversions = {
            'class': 'className',
            'for': 'htmlFor',
            'tabindex': 'tabIndex',
            'readonly': 'readOnly',
            'maxlength': 'maxLength',
            'cellpadding': 'cellPadding',
            'cellspacing': 'cellSpacing',
            'rowspan': 'rowSpan',
            'colspan': 'colSpan',
            'usemap': 'useMap',
            'frameborder': 'frameBorder',
        }
        
        return conversions.get(attr_name.lower(), attr_name)
    
    def _escape_attr(self, text: str) -> str:
        """Escape attribute values for JSX."""
        if not text:
            return text
        # Escape double quotes and other special characters
        text = text.replace('\\', '\\\\')  # Escape backslashes first
        text = text.replace('"', '\\"')    # Escape double quotes
        text = text.replace('\n', '\\n')   # Escape newlines
        text = text.replace('\r', '\\r')   # Escape carriage returns
        text = text.replace('\t', '\\t')   # Escape tabs
        return text

    def get_jsx_imports(self) -> str:
        """Generate JSX import statements for used components."""
        if not self.jsx_components_used:
            return ""
        
        imports = []
        for component in sorted(self.jsx_components_used):
            imports.append(f"import {{ {component} }} from '../components/{component}';")
        
        return '\n'.join(imports)