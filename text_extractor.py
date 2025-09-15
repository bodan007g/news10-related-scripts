#!/usr/bin/env python3
"""
Text Extractor Script
Extracts clean article text from HTML files using generic and website-specific rules.
"""

import os
import json
import yaml
from datetime import datetime

# Configuration
import trafilatura
from newspaper import Article
from text_cleanup import MultiLanguageTextCleaner
import time
CONTENT_DIR = "content"
LOGS_DIR = "logs"
STATUS_FILE = "text_extractor_status.json"

class TextExtractor:
    def __init__(self, extraction_method='trafilatura', save_cleaned_html=False, domain_filter=None):
        """
        Initialize TextExtractor
        
        Args:
            extraction_method (str): 'trafilatura' (default) or 'newspaper'
            save_cleaned_html (bool): If True, save cleaned HTML next to original files
            domain_filter (str): If provided, only process files from this domain (e.g., 'www.digi24.ro' or 'digi24.ro')
        """
        if extraction_method not in ['trafilatura', 'newspaper']:
            raise ValueError("extraction_method must be 'trafilatura' or 'newspaper'")
        
        self.extraction_method = extraction_method
        self.save_cleaned_html = save_cleaned_html
        self.original_domain_filter = domain_filter
        self.domain_filter = self.normalize_domain(domain_filter) if domain_filter else None
        self.text_cleaner = MultiLanguageTextCleaner()
        self.processed_status = self.load_status()
        self.stats = {
            'total_processed': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'already_processed': 0,
            'skipped_files': 0
        }  # Don't wrap lines  # Don't wrap lines  # Don't wrap lines

    def normalize_domain(self, domain):
        """
        Normalize domain names to their full form
        
        Args:
            domain (str): Domain name (e.g., 'digi24.ro' or 'www.digi24.ro')
            
        Returns:
            str: Normalized domain name (e.g., 'www.digi24.ro')
        """
        if not domain:
            return domain
            
        # Domain mapping for short forms to full forms
        domain_mapping = {
            'digi24.ro': 'www.digi24.ro',
            'bzi.ro': 'www.bzi.ro',
            'lemonde.fr': 'www.lemonde.fr'
        }
        
        # If it's already a full domain (starts with www.), return as-is
        if domain.startswith('www.'):
            return domain
            
        # If it's a known short form, map to full form
        if domain in domain_mapping:
            normalized = domain_mapping[domain]
            return normalized
            
        # If it's an unknown short form, try adding www.
        if not domain.startswith('www.'):
            normalized = f"www.{domain}"
            return normalized
            
        return domain

    def load_status(self):
        """Load processing status from file"""
        if os.path.exists(STATUS_FILE):
            try:
                with open(STATUS_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def save_status(self):
        """Save processing status to file"""
        with open(STATUS_FILE, 'w') as f:
            json.dump(self.processed_status, f, indent=2)

    def log_skip_reason(self, file_path, domain, skip_type, reason, details=None):
        """Log detailed skip reasons to both console and log file"""
        now = datetime.now()
        month_str = now.strftime("%Y-%m")
        month_dir = os.path.join(LOGS_DIR, month_str)
        os.makedirs(month_dir, exist_ok=True)
        
        skip_log_path = os.path.join(month_dir, "text_extractor_skipped.log")
        
        # Create log entry
        log_entry = {
            'timestamp': now.isoformat(),
            'file_path': file_path,
            'domain': domain,
            'skip_type': skip_type,
            'reason': reason,
            'details': details or {}
        }
        
        # Write to log file
        with open(skip_log_path, "a", encoding="utf-8") as f:
            f.write(f"{json.dumps(log_entry, ensure_ascii=False)}\n")
        
        # Also write human-readable version
        human_log_path = os.path.join(month_dir, "text_extractor_skipped_readable.log")
        with open(human_log_path, "a", encoding="utf-8") as f:
            f.write(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] {skip_type.upper()}: {file_path}\n")
            f.write(f"  Domain: {domain}\n")
            f.write(f"  Reason: {reason}\n")
            if details:
                for key, value in details.items():
                    f.write(f"  {key}: {value}\n")
            f.write("\n")

    def clean_html_for_extraction(self, html_content):
        """
        Clean HTML by removing non-content elements while preserving structure
        
        Args:
            html_content (str): Original HTML content
            
        Returns:
            str: Cleaned HTML with only content-relevant elements
        """
        try:
            import re
            from bs4 import BeautifulSoup, Comment
            
            # Remove HTML comments first
            html_content = re.sub(r'<!--.*?-->', '', html_content, flags=re.DOTALL)
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove any remaining comments (BeautifulSoup parsing)
            for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
                comment.extract()
            
            # Remove unwanted elements
            unwanted_tags = [
                'script', 'style', 'nav', 'footer', 'aside',
                'iframe', 'embed', 'object', 'applet', 'form',
                'button', 'input', 'textarea', 'select', 'option',
                'noscript', 'meta', 'link', 'title'
            ]
            
            for tag_name in unwanted_tags:
                for tag in soup.find_all(tag_name):
                    tag.decompose()
            
            # Remove page navigation headers but preserve article headers
            for header in soup.find_all('header'):
                # Keep headers that likely contain article content (title, subtitle)
                if (header.find(['h1', 'h2', 'h3']) or 
                    'article' in str(header.get('class', '')).lower() or
                    'title' in str(header.get('class', '')).lower() or
                    len(header.get_text(strip=True)) > 30):  # Likely article header with substantial content
                    continue
                else:
                    header.decompose()  # Remove page navigation headers
            
            # Remove elements with common non-content classes/ids
            unwanted_selectors = [
                '[class*="advertisement"]', '[class*="ad-"]', '[class*="ads"]',
                '[class*="sidebar"]', '[class*="widget"]', '[class*="menu"]',
                '[class*="nav"]', '[class*="header"]', '[class*="footer"]',
                '[class*="social"]', '[class*="share"]', '[class*="comment"]',
                '[id*="advertisement"]', '[id*="ad-"]', '[id*="ads"]',
                '[id*="sidebar"]', '[id*="widget"]', '[id*="menu"]',
                '[id*="nav"]', '[id*="header"]', '[id*="footer"]'
            ]
            
            for selector in unwanted_selectors:
                for element in soup.select(selector):
                    element.decompose()
            
            # Remove inline styles and other unwanted attributes
            for element in soup.find_all():
                if element.name:
                    # Remove style attribute
                    if 'style' in element.attrs:
                        del element.attrs['style']
                    # Remove other unwanted attributes while keeping essential ones
                    attrs_to_keep = ['href', 'src', 'alt', 'title']
                    element.attrs = {k: v for k, v in element.attrs.items() if k in attrs_to_keep}
            
            # Remove empty elements (except br, hr, img)
            for element in soup.find_all():
                if element.name not in ['br', 'hr', 'img'] and not element.get_text(strip=True):
                    element.decompose()
            
            # Convert to string and clean up multiple consecutive empty lines
            cleaned_html = str(soup)
            
            # Remove multiple consecutive empty lines (keep at most 2 consecutive newlines)
            cleaned_html = re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned_html)
            
            # Remove excessive whitespace between tags while preserving content spacing
            cleaned_html = re.sub(r'>\s{3,}<', '>\n<', cleaned_html)
            
            # Remove leading spaces/tabs on each line (trim each line)
            cleaned_html = re.sub(r'^[ \t]+', '', cleaned_html, flags=re.MULTILINE)
            
            return cleaned_html
            
        except Exception as e:
            print(f"HTML cleaning failed: {e}")
            return html_content  # Return original if cleaning fails  # Return original if cleaning fails  # Return original if cleaning fails  # Return original if cleaning fails

    def clean_html_lightly_for_newspaper(self, html_content):
        """
        Light HTML cleaning specifically for newspaper3k extraction
        Preserves more structure that newspaper3k needs while removing obviously unwanted content
        
        Args:
            html_content (str): Original HTML content
            
        Returns:
            str: Lightly cleaned HTML with preserved content structure for newspaper3k
        """
        try:
            import re
            from bs4 import BeautifulSoup, Comment
            
            # Remove HTML comments first
            html_content = re.sub(r'<!--.*?-->', '', html_content, flags=re.DOTALL)
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove any remaining comments (BeautifulSoup parsing)
            for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
                comment.extract()
            
            # Remove clearly unwanted elements (more conservative than the aggressive cleaner)
            unwanted_tags = [
                'script', 'style', 'nav', 'footer', 'aside',
                'iframe', 'embed', 'object', 'applet',
                'noscript', 'meta', 'link', 'title'
            ]
            
            for tag_name in unwanted_tags:
                for tag in soup.find_all(tag_name):
                    tag.decompose()
            
            # Remove obvious advertisement elements (more conservative)
            unwanted_selectors = [
                '[class*="advertisement"]', '[class*="ads"]',
                '[id*="advertisement"]', '[id*="ads"]'
            ]
            
            for selector in unwanted_selectors:
                for element in soup.select(selector):
                    element.decompose()
            
            # Remove only style attributes but keep other attributes that might help with content identification
            for element in soup.find_all():
                if element.name and 'style' in element.attrs:
                    del element.attrs['style']
            
            # Convert to string and do minimal text cleanup
            cleaned_html = str(soup)
            
            # Remove excessive whitespace but be more conservative
            cleaned_html = re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned_html)
            
            return cleaned_html
            
        except Exception as e:
            print(f"Light HTML cleaning failed: {e}")
            return html_content  # Return original if cleaning fails

    def load_domain_extraction_rules(self, domain):
        """Load domain-specific extraction rules from YAML file"""
        config_file = os.path.join("extraction_rules", f"{domain}.yaml")
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Warning: Could not load extraction rules for {domain}: {e}")
        return {}

    def extract_custom_sections(self, soup, domain, url=None):
        """
        Extract custom content sections defined in domain rules
        
        Args:
            soup: BeautifulSoup object of cleaned HTML
            domain (str): Domain name for loading rules
            url (str): Original article URL for fallback extraction
            
        Returns:
            str: Formatted custom sections content or empty string
        """
        try:
            rules = self.load_domain_extraction_rules(domain)
            custom_sections = rules.get('custom_content_sections', {})
            
            if not custom_sections.get('enabled', False):
                return ""
            
            sections = custom_sections.get('sections', [])
            if not sections:
                return ""
            
            # Sort sections by order field
            sections = sorted(sections, key=lambda x: x.get('order', 999))
            
            sections_content = []
            processing_options = custom_sections.get('processing_options', {})
            
            for section in sections:
                content = self.extract_section_content(soup, section, processing_options, url)
                if content:
                    sections_content.append(content)
            
            return self.format_custom_sections(sections_content, processing_options)
            
        except Exception as e:
            print(f"Warning: Custom sections extraction failed for {domain}: {e}")
            return ""

    def extract_section_content(self, soup, section_config, processing_options, url=None):
        """
        Extract content for a specific custom section
        
        Args:
            soup: BeautifulSoup object
            section_config (dict): Section configuration from YAML
            processing_options (dict): Global processing options
            url (str): Original article URL for fallback extraction
            
        Returns:
            str: Formatted section content or None if not found
        """
        try:
            selectors = section_config.get('selectors', [])
            fallback_selectors = section_config.get('fallback_selectors', [])
            section_name = section_config.get('name', '')
            
            # Try primary selectors first
            content = self.try_selectors(soup, selectors)
            
            # Try fallback selectors if no content found
            if not content and fallback_selectors:
                content = self.try_selectors(soup, fallback_selectors)
            
            # For title sections, try URL extraction if HTML selectors failed
            if not content and section_name == "title" and url:
                # Extract domain from the soup's context or use a passed domain
                # We'll get domain from the URL
                from urllib.parse import urlparse
                parsed_url = urlparse(url)
                domain = parsed_url.netloc
                
                url_title = self.extract_title_from_url(url, domain)
                if url_title:
                    content = url_title
                    print(f"📖 Extracted title from URL for {domain}")
            
            if not content:
                return None
            
            # Apply section-specific processing patterns
            section_processing = section_config.get('processing', {})
            clean_patterns = section_processing.get('clean_patterns', [])
            
            for pattern in clean_patterns:
                import re
                content = re.sub(pattern, '', content).strip()
            
            # Apply global processing options
            if processing_options.get('trim_whitespace', True):
                content = content.strip()
            
            # Check maximum length
            max_length = processing_options.get('max_section_length', 500)
            if len(content) > max_length:
                content = content[:max_length].rsplit(' ', 1)[0] + "..."
            
            # Skip if empty after processing
            if not content:
                return None
            
            # Apply formatting template
            format_template = section_config.get('format', '{content}')
            return format_template.format(content=content)
            
        except Exception as e:
            print(f"Warning: Section content extraction failed: {e}")
            return None

    def try_selectors(self, soup, selectors):
        """
        Try multiple CSS selectors to find content, including special JavaScript extraction
        
        Args:
            soup: BeautifulSoup object
            selectors (list): List of CSS selectors to try
            
        Returns:
            str: First found content or empty string
        """
        for selector in selectors:
            try:
                # Special handling for JavaScript extraction
                if selector.startswith('js:'):
                    content = self.extract_from_javascript(soup, selector[3:])
                    if content:
                        return content
                    continue
                
                # Regular CSS selector
                elements = soup.select(selector)
                for element in elements:
                    # Special handling for meta tags - extract from content attribute
                    if element.name == 'meta' and element.has_attr('content'):
                        content = element['content'].strip()
                        if content and len(content) > 3:
                            return content
                    else:
                        # Regular text extraction
                        text = element.get_text(strip=True)
                        if text and len(text) > 3:  # Found meaningful content
                            return text
            except Exception as e:
                print(f"Warning: Selector '{selector}' failed: {e}")
                continue
        return ""

    def extract_from_javascript(self, soup, js_path):
        """
        Extract content from JavaScript variables embedded in script tags
        
        Args:
            soup: BeautifulSoup object
            js_path (str): JavaScript path like 'lmd.context.article.title'
            
        Returns:
            str: Extracted content or empty string
        """
        try:
            import json
            import re
            import html
            from bs4 import BeautifulSoup as BS
            
            # Find all script tags
            script_tags = soup.find_all('script')
            
            for script in script_tags:
                script_content = script.string if script.string else ""
                
                # Look for variable declarations that might contain our data
                # Handle different patterns: var lmd = {...}, window.lmd = {...}, etc.
                var_patterns = [
                    rf'var\s+{js_path.split(".")[0]}\s*=\s*({{.*?}});',
                    rf'window\.{js_path.split(".")[0]}\s*=\s*({{.*?}});',
                    rf'{js_path.split(".")[0]}\s*=\s*({{.*?}});'
                ]
                
                for pattern in var_patterns:
                    matches = re.search(pattern, script_content, re.DOTALL | re.MULTILINE)
                    if matches:
                        try:
                            # Parse the JSON object
                            json_str = matches.group(1)
                            data = json.loads(json_str)
                            
                            # Navigate the object path
                            path_parts = js_path.split('.')[1:]  # Skip the variable name
                            current = data
                            
                            for part in path_parts:
                                if isinstance(current, dict) and part in current:
                                    current = current[part]
                                else:
                                    current = None
                                    break
                            
                            if current and isinstance(current, str):
                                # Clean up HTML content: decode entities and strip tags
                                decoded = html.unescape(current)  # Decode HTML entities like &nbsp;
                                soup_temp = BS(decoded, 'html.parser')
                                clean_text = soup_temp.get_text(separator=' ', strip=True)  # Strip HTML tags with space separator
                                return clean_text
                                
                        except (json.JSONDecodeError, KeyError) as e:
                            print(f"Warning: Failed to parse JavaScript data: {e}")
                            continue
            
            return ""
            
        except Exception as e:
            print(f"Warning: JavaScript extraction failed: {e}")
            return ""

    def format_custom_sections(self, sections_content, processing_options):
        """
        Format multiple custom sections into final content
        
        Args:
            sections_content (list): List of formatted section strings
            processing_options (dict): Processing options from YAML
            
        Returns:
            str: Formatted sections content
        """
        if not sections_content:
            return ""
        
        # Remove empty sections if requested
        if processing_options.get('remove_empty_sections', True):
            sections_content = [s for s in sections_content if s.strip()]
        
        if not sections_content:
            return ""
        
        # Join sections with separator
        separator = processing_options.get('separator', '\n\n')
        if processing_options.get('add_separator_between_sections', True):
            return separator.join(sections_content)
        else:
            return '\n'.join(sections_content)

    def check_duplicate_content(self, custom_content, main_content, threshold=0.8):
        """
        Check if custom content is already present in main content
        
        Args:
            custom_content (str): Custom sections content
            main_content (str): Main article content
            threshold (float): Similarity threshold (0.0-1.0)
            
        Returns:
            bool: True if content appears to be duplicate
        """
        if not custom_content or not main_content:
            return False
        
        # Simple check: if significant portion of custom content appears in main content
        custom_words = set(custom_content.lower().split())
        main_words = set(main_content.lower().split())
        
        if len(custom_words) < 3:  # Too short to check meaningfully
            return False
        
        # Calculate overlap
        overlap = len(custom_words.intersection(main_words))
        similarity = overlap / len(custom_words)
        
        return similarity >= threshold

    def extract_title_from_url(self, url, domain):
        """
        Extract article title from URL for sites where HTML title is missing
        
        Args:
            url (str): Article URL
            domain (str): Domain name
            
        Returns:
            str: Extracted title or empty string
        """
        try:
            import re
            from urllib.parse import urlparse
            
            # Domain-specific URL title extraction patterns
            if domain == "www.lemonde.fr":
                # Le Monde URLs: extract slug and convert to readable title
                # Example: katrina-l-ouragan-infernal-sur-netflix-vingt-ans-apres-spike-lee-prend-le-pouls-de-la-nouvelle-orleans
                parsed = urlparse(url)
                path = parsed.path
                
                # Extract the article slug (last part before article ID)
                # Pattern: /article-slug_ARTICLEID_CATEGORYID.html
                match = re.search(r'/([^/]+)_\d+_\d+\.html$', path)
                if match:
                    slug = match.group(1)
                    
                    # Convert slug to readable title
                    title = self.convert_slug_to_title(slug, "fr")
                    return title
                    
            elif domain == "www.bzi.ro":
                # BZI.ro URLs: similar pattern
                parsed = urlparse(url)
                path = parsed.path
                
                # Extract the article slug (before article ID)
                match = re.search(r'/([^/]+)-\d+$', path)
                if match:
                    slug = match.group(1)
                    title = self.convert_slug_to_title(slug, "ro")
                    return title
                    
            elif domain == "www.digi24.ro":
                # Digi24.ro URLs: similar pattern
                parsed = urlparse(url)
                path = parsed.path
                
                # Extract the article slug (before article ID)
                match = re.search(r'/([^/]+)-(\d+)$', path)
                if match:
                    slug = match.group(1)
                    title = self.convert_slug_to_title(slug, "ro")
                    return title
                    
            return ""
            
        except Exception as e:
            print(f"Warning: URL title extraction failed: {e}")
            return ""

    def convert_slug_to_title(self, slug, language):
        """
        Convert URL slug to readable title
        
        Args:
            slug (str): URL slug with dashes
            language (str): Language code (fr, ro, en)
            
        Returns:
            str: Readable title
        """
        try:
            # Replace dashes with spaces
            words = slug.split('-')
            
            # Language-specific title formatting
            if language == "fr":
                # French: capitalize first word and proper nouns
                formatted_words = []
                for i, word in enumerate(words):
                    if i == 0:
                        # Capitalize first word
                        formatted_words.append(word.capitalize())
                    elif word.lower() in ['le', 'la', 'les', 'de', 'du', 'des', 'à', 'au', 'aux', 'et', 'ou', 'pour', 'sur', 'avec', 'sans', 'dans', 'par', 'un', 'une']:
                        # Keep articles and prepositions lowercase
                        formatted_words.append(word.lower())
                    elif len(word) > 3:
                        # Capitalize longer words (likely proper nouns or important words)
                        formatted_words.append(word.capitalize())
                    else:
                        formatted_words.append(word.lower())
                        
            elif language == "ro":
                # Romanian: similar rules
                formatted_words = []
                for i, word in enumerate(words):
                    if i == 0:
                        formatted_words.append(word.capitalize())
                    elif word.lower() in ['de', 'la', 'în', 'cu', 'pe', 'din', 'pentru', 'prin', 'după', 'înainte', 'fără', 'și', 'sau', 'dar', 'iar', 'un', 'o']:
                        formatted_words.append(word.lower())
                    elif len(word) > 3:
                        formatted_words.append(word.capitalize())
                    else:
                        formatted_words.append(word.lower())
                        
            else:
                # Default: capitalize each word except short articles/prepositions
                formatted_words = []
                for i, word in enumerate(words):
                    if i == 0:
                        formatted_words.append(word.capitalize())
                    elif word.lower() in ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by']:
                        formatted_words.append(word.lower())
                    else:
                        formatted_words.append(word.capitalize())
            
            return ' '.join(formatted_words)
            
        except Exception as e:
            print(f"Warning: Slug conversion failed: {e}")
            # Fallback: simple title case
            return slug.replace('-', ' ').title()

    def preserve_html_formatting(self, html_content):
        """
        Convert HTML formatting to Markdown before text extraction
        Preserves bold, italic, and other important formatting
        
        Args:
            html_content (str): Original HTML content
            
        Returns:
            str: HTML with Markdown formatting markers
        """
        try:
            from bs4 import BeautifulSoup, NavigableString
            import re
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Convert bold tags to Markdown - handle complex nested content
            for tag in soup.find_all(['b', 'strong']):
                # Get all text content from the tag, preserving nested structure
                text_content = self._get_formatted_content(tag)
                if text_content.strip():
                    # Replace the entire tag with Markdown-wrapped content
                    new_content = f"**{text_content}**"
                    tag.replace_with(BeautifulSoup(new_content, 'html.parser'))
            
            # Convert italic tags to Markdown
            for tag in soup.find_all(['i', 'em']):
                text_content = self._get_formatted_content(tag)
                if text_content.strip():
                    new_content = f"*{text_content}*"
                    tag.replace_with(BeautifulSoup(new_content, 'html.parser'))
            
            # Convert underline tags to Markdown (using HTML since Markdown doesn't have native underline)
            for tag in soup.find_all('u'):
                text_content = self._get_formatted_content(tag)
                if text_content.strip():
                    new_content = f"<u>{text_content}</u>"
                    tag.replace_with(BeautifulSoup(new_content, 'html.parser'))
            
            # Convert code tags to Markdown
            for tag in soup.find_all(['code', 'tt']):
                text_content = self._get_formatted_content(tag)
                if text_content.strip():
                    new_content = f"`{text_content}`"
                    tag.replace_with(BeautifulSoup(new_content, 'html.parser'))
            
            # Convert blockquotes to Markdown
            for tag in soup.find_all('blockquote'):
                text_content = tag.get_text()
                if text_content.strip():
                    lines = text_content.strip().split('\n')
                    quoted_lines = [f"> {line.strip()}" for line in lines if line.strip()]
                    new_content = '\n'.join(quoted_lines) + '\n'
                    tag.replace_with(BeautifulSoup(new_content, 'html.parser'))
            
            # Handle headers - preserve them as HTML since we have header detection later
            # This ensures consistent header processing
            
            # Clean up multiple spaces and newlines that might have been introduced
            formatted_html = str(soup)
            
            # Clean up extra spaces around Markdown markers
            formatted_html = re.sub(r'\*\*\s+', '**', formatted_html)
            formatted_html = re.sub(r'\s+\*\*', '**', formatted_html)
            formatted_html = re.sub(r'(?<!\*)\*\s+', '*', formatted_html)
            formatted_html = re.sub(r'\s+\*(?!\*)', '*', formatted_html)
            formatted_html = re.sub(r'`\s+', '`', formatted_html)
            formatted_html = re.sub(r'\s+`', '`', formatted_html)
            
            return formatted_html
            
        except Exception as e:
            print(f"HTML formatting preservation failed: {e}")
            return html_content  # Return original if processing fails
    
    def _get_formatted_content(self, tag):
        """
        Extract formatted content from a tag, preserving nested links and other elements
        
        Args:
            tag: BeautifulSoup tag object
            
        Returns:
            str: Formatted content with preserved nested elements
        """
        try:
            content_parts = []
            
            for element in tag.contents:
                if isinstance(element, NavigableString):
                    # Direct text content
                    content_parts.append(str(element))
                elif element.name == 'a':
                    # Preserve links in a readable format
                    link_text = element.get_text()
                    link_url = element.get('href', '')
                    if link_url:
                        content_parts.append(f"[{link_text}]({link_url})")
                    else:
                        content_parts.append(link_text)
                elif element.name in ['br']:
                    # Handle line breaks
                    content_parts.append(' ')
                else:
                    # For other nested elements, just get the text
                    content_parts.append(element.get_text())
            
            return ''.join(content_parts)
            
        except Exception as e:
            # Fallback to simple text extraction
            return tag.get_text()  # Return original if processing fails

    def clean_markdown_formatting(self, text):
        """
        Clean up Markdown formatting in extracted text
        Fixes common issues that occur during HTML to text extraction
        
        Args:
            text (str): Extracted text with potential formatting issues
            
        Returns:
            str: Cleaned text with proper Markdown formatting
        """
        try:
            import re
            
            if not text:
                return text
            
            # Fix broken bold formatting ONLY when it's clearly broken across lines within a sentence
            # Don't remove newlines that separate paragraphs or sections
            # Only fix if there's text immediately before and after the break (indicating broken formatting)
            # Use [ \t] to match only spaces and tabs, not newlines
            text = re.sub(r'(\w)\*\*[ \t]*\n[ \t]*(\w)', r'\1**\2', text)  # Fix broken bold within text
            text = re.sub(r'(\w)[ \t]*\n[ \t]*\*\*(\w)', r'\1**\2', text)  # Fix broken bold within text
            
            # Fix broken italic formatting (same logic)
            text = re.sub(r'(\w)\*[ \t]*\n[ \t]*(\w)', r'\1*\2', text)
            text = re.sub(r'(\w)[ \t]*\n[ \t]*\*(?!\*)(\w)', r'\1*\2', text)
            
            # Fix broken code formatting (same logic)
            text = re.sub(r'(\w)`[ \t]*\n[ \t]*(\w)', r'\1`\2', text)
            text = re.sub(r'(\w)[ \t]*\n[ \t]*`(\w)', r'\1`\2', text)
            
            # Remove empty bold/italic tags - FIXED: be more specific to avoid matching valid bold formatting
            text = re.sub(r'\*\*\s*\*\*', '', text)  # Remove empty bold tags like ** **
            # FIXED: Only match single * followed by whitespace and another single * (true empty italic tags)
            # This avoids matching ** (bold markers)
            text = re.sub(r'(?<!\*)\*\s+\*(?!\*)', '', text)  # Remove empty italic tags like * * but not **
            text = re.sub(r'``', '', text)  # Remove empty code tags
            
            # Fix multiple consecutive formatting markers
            text = re.sub(r'\*{3,}', '**', text)
            
            # Ensure proper spacing around formatting - but don't break existing good formatting
            # Only add space before bold if there's no space already
            text = re.sub(r'(\w)(\*\*\w)', r'\1 \2', text)  # Add space before bold if missing
            # Only add space before italic if there's no space already and it's not part of bold
            text = re.sub(r'(\w)(\*(?!\*)\w)', r'\1 \2', text)  # Add space before italic if missing
            
            # Clean up excessive whitespace but preserve paragraph breaks
            # Replace multiple spaces (but not newlines) with single space
            text = re.sub(r'[ \t]{2,}', ' ', text)
            # Replace more than 2 consecutive newlines with exactly 2 (paragraph break)
            text = re.sub(r'\n{3,}', '\n\n', text)
            # Remove trailing spaces from lines
            text = re.sub(r'[ \t]+\n', '\n', text)
            
            # Fix blockquote formatting that may have been disrupted
            lines = text.split('\n')
            cleaned_lines = []
            
            for line in lines:
                # Fix broken blockquotes
                if '>' in line and not line.strip().startswith('>'):
                    # Try to fix malformed blockquotes
                    if line.strip().startswith('> '):
                        cleaned_lines.append(line)
                    else:
                        cleaned_lines.append(line)
                else:
                    cleaned_lines.append(line)
            
            return '\n'.join(cleaned_lines)
            
        except Exception as e:
            print(f"Markdown formatting cleanup failed: {e}")
            return text  # Return original if processing fails  # Return original if processing fails  # Return original if processing fails  # Return original if processing fails  # Return original if processing fails

    def ensure_proper_paragraphs(self, text):
        """
        Ensure proper paragraph separation in extracted text
        
        Args:
            text (str): Extracted text that may have missing paragraph breaks
            
        Returns:
            str: Text with proper paragraph separation
        """
        try:
            import re
            
            if not text:
                return text
            
            lines = text.split('\n')
            processed_lines = []
            
            for i, line in enumerate(lines):
                stripped_line = line.strip()
                
                # Skip empty lines
                if not stripped_line:
                    processed_lines.append(line)
                    continue
                
                # Add current line
                processed_lines.append(line)
                
                # Check if this line should be followed by a paragraph break
                # Heuristics for paragraph endings:
                # 1. Lines ending with sentence-ending punctuation
                # 2. Followed by a line that starts a new thought/sentence
                # 3. Not if the next line is a header or already has spacing
                
                if i < len(lines) - 1:  # Not the last line
                    next_line = lines[i + 1].strip()
                    
                    # Check if current line ends a sentence/paragraph
                    ends_sentence = stripped_line.endswith(('.', '!', '?', '"', '"', '".', '".', '".'))
                    
                    # Check if next line starts a new paragraph/thought
                    starts_new_thought = (
                        next_line and  # Next line has content
                        not next_line.startswith(('#', '>', '-', '*', '1.', '2.', '3.')) and  # Not a header, quote, or list
                        (next_line[0].isupper() or next_line.startswith('"') or next_line.startswith('"')) and  # Starts with capital or quote
                        not any(next_line.startswith(word) for word in ['și ', 'dar ', 'iar ', 'sau ', 'însă ', 'pentru că ', 'deoarece '])  # Not a continuation word
                    )
                    
                    # Add paragraph break if conditions are met
                    if (ends_sentence and starts_new_thought and 
                        next_line != '' and  # Next line is not empty
                        len(processed_lines) > 0 and processed_lines[-1].strip() != ''):  # Current line is not empty
                        
                        # Check if there's already a paragraph break
                        if i + 1 < len(lines) and lines[i + 1].strip() == '':
                            continue  # Already has spacing
                        
                        # Add paragraph break
                        processed_lines.append('')
            
            return '\n'.join(processed_lines)
            
        except Exception as e:
            print(f"Paragraph processing failed: {e}")
            return text  # Return original if processing fails







    def extract_with_trafilatura(self, html_content, original_url=""):
        """Extract article content using trafilatura"""
        try:
            # Extract text content
            text = trafilatura.extract(html_content, 
                                     include_comments=False,
                                     include_tables=True,
                                     include_links=False,
                                     url=original_url)
            
            # For trafilatura, we need to manually add paragraph breaks
            if text:
                # Split by single newlines and process
                lines = text.split('\n')
                formatted_lines = []
                
                for line in lines:
                    stripped = line.strip()
                    if stripped:  # Non-empty line
                        formatted_lines.append(stripped)
                    elif formatted_lines and formatted_lines[-1]:  # Empty line after content
                        formatted_lines.append('')  # Keep as paragraph separator
                
                # Join lines and ensure proper paragraph spacing
                text = '\n'.join(formatted_lines)
                # Convert single newlines between content to double newlines
                import re
                text = re.sub(r'\n(?=\S)', '\n\n', text)
            
            # Extract metadata (without fast parameter)
            metadata = trafilatura.extract_metadata(html_content)
            
            return text, metadata
        except Exception as e:
            print(f"Trafilatura extraction failed for {original_url}: {e}")
            return None, None

    def extract_with_newspaper(self, html_content, original_url=""):
        """Extract article content using newspaper3k"""
        try:
            # Create Article object
            article = Article(original_url)
            article.set_html(html_content)
            article.parse()
            
            # Add empty lines between paragraphs
            text = article.text
            if text:
                # Split by double newlines (existing paragraph breaks)
                paragraphs = text.split('\n\n')
                # Join with double empty lines for better spacing
                text = '\n\n'.join(paragraph.strip() for paragraph in paragraphs if paragraph.strip())
            
            # Create metadata object similar to trafilatura
            class NewspaperMetadata:
                def __init__(self, article):
                    self.title = article.title
                    self.author = ', '.join(article.authors) if article.authors else None
                    self.date = article.publish_date.strftime('%Y-%m-%d') if article.publish_date else None
                    self.url = original_url
            
            metadata = NewspaperMetadata(article)
            
            return text, metadata
            
        except Exception as e:
            print(f"Newspaper3k extraction failed for {original_url}: {e}")
            return None, None

    def format_headers_markdown(self, text, html_content=""):
        """Format headers in text with proper Markdown syntax"""
        if not text:
            return text
        
        # First, try to identify headers from HTML structure if available
        html_headers = {}
        if html_content:
            try:
                from bs4 import BeautifulSoup
                import unicodedata
                
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Find all header tags and map their text to header levels
                for level in range(1, 7):  # h1 to h6
                    headers = soup.find_all(f'h{level}')
                    for header in headers:
                        header_text = header.get_text(strip=True)
                        if header_text and len(header_text) > 3:
                            # Normalize text for better matching
                            normalized = unicodedata.normalize('NFKC', header_text)
                            html_headers[normalized] = level
                            # Also store original for exact matching
                            html_headers[header_text] = level
            except Exception as e:
                # If HTML parsing fails, fall back to heuristic method
                pass
        
        lines = text.split('\n')
        formatted_lines = []
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                formatted_lines.append(line)
                continue
                
            # Check if this text matches a header from HTML
            is_header = False
            header_level = 1
            
            # Try exact match first
            if stripped in html_headers:
                is_header = True
                header_level = html_headers[stripped]
            else:
                # Try normalized match
                try:
                    import unicodedata
                    normalized = unicodedata.normalize('NFKC', stripped)
                    if normalized in html_headers:
                        is_header = True
                        header_level = html_headers[normalized]
                except:
                    pass
            
            if not is_header:
                # Fallback to heuristic detection for headers not found in HTML
                # Check if this looks like a header
                # Heuristics for detecting headers:
                # 1. Short lines (typically under 80 chars)
                # 2. No ending punctuation (., !, :, ;, ,) - Allow ? for question headers  
                # 3. Followed by content or empty line
                # 4. Not starting with common content words
                
                if (len(stripped) < 80 and 
                    len(stripped) > 5 and
                    not stripped.endswith(('.', '!', ':', ';', ',') ) and  # Allow ? for question headers
                    not stripped.startswith(('În ', 'De ', 'Cu ', 'Pentru ', 'Prin ', 'Astfel', 'Așa', 'Dar', 'Și')) and
                    # Check if next non-empty line exists and looks like content
                    self._next_line_looks_like_content(lines, i)):
                    
                    is_header = True
                    
                    # Determine header level based on context and formatting
                    if i == 0 or (i < 3 and not any(formatted_lines[-3:])):  # First meaningful line
                        header_level = 1
                    elif any(keyword in stripped.lower() for keyword in ['actualizare', 'știrea inițială', 'concluzia', 'background', 'ce s-a întâmplat']):
                        header_level = 2
                    else:
                        header_level = 2  # Default secondary header
            
            if is_header:
                # Ensure empty line before header (but not if it's the first line or already has empty line)
                if (i > 0 and formatted_lines and 
                    formatted_lines[-1].strip() != "" and  # Previous line is not empty
                    not formatted_lines[-1].startswith('#')):  # Previous line is not already a header
                    formatted_lines.append("")  # Add empty line before header
                
                # Format as Markdown header
                header_line = f"{'#' * header_level} {stripped}"
                formatted_lines.append(header_line)
                # Add underline for emphasis if requested
                if header_level == 1:
                    formatted_lines.append("=" * len(header_line))
                elif header_level == 2:
                    formatted_lines.append("-" * len(header_line))
            else:
                formatted_lines.append(line)
                
        return '\n'.join(formatted_lines)
    
    def _next_line_looks_like_content(self, lines, current_index):
        """Check if the next non-empty line looks like content rather than another header"""
        for i in range(current_index + 1, min(len(lines), current_index + 3)):
            if i < len(lines) and lines[i].strip():
                next_line = lines[i].strip()
                # Content indicators: longer lines, starts with common content words, ends with punctuation
                return (len(next_line) > 50 or 
                       next_line.endswith(('.', '!', '?', ':', ';')) or
                       any(next_line.startswith(word) for word in ['În ', 'De ', 'Cu ', 'Pentru ', 'Prin ', 'Acest', 'Potrivit', 'După']))
        return False

    def reconstruct_url(self, domain, file_path):
        """Reconstruct original URL from file path"""
        # Extract path from filename
        filename = os.path.basename(file_path)
        if filename == 'index.html':
            return f"https://{domain}/"
        
        # Remove .html extension and convert underscores back to slashes
        url_path = filename.replace('.html', '').replace('_', '/')
        return f"https://{domain}/{url_path}"

    def process_html_file(self, file_path, domain):
        """Process a single HTML file using the selected extraction method"""
        file_key = f"{domain}:{file_path}"
        
        try:
            # Read HTML content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                original_html_content = f.read()
            
            # Check for empty or very small HTML files
            if len(original_html_content.strip()) < 200:
                self.stats['skipped_files'] += 1
                reason = f"HTML file too small ({len(original_html_content)} chars)"
                print(f"⚠️  Skipping ({domain}): {reason}")
                self.log_skip_reason(file_path, domain, "html_too_small", reason)
                self.processed_status[file_key] = {
                    'status': 'skipped',
                    'reason': reason,
                    'processed_at': datetime.now().isoformat()
                }
                return
            
            # Preserve formatting before cleaning
            formatted_html_content = self.preserve_html_formatting(original_html_content)
            
            # Reconstruct original URL
            original_url = self.reconstruct_url(domain, file_path)
            
            # Use different cleaning strategies based on extraction method
            if self.extraction_method == 'trafilatura':
                # Trafilatura is robust, use more aggressive cleaning
                cleaned_html_content = self.clean_html_for_extraction(formatted_html_content)
                
                # Check if cleaning removed too much content
                if len(cleaned_html_content.strip()) < 100:
                    self.stats['skipped_files'] += 1
                    reason = f"HTML cleaning left too little content ({len(cleaned_html_content)} chars)"
                    print(f"⚠️  Skipping ({domain}): {reason}")
                    self.log_skip_reason(file_path, domain, "cleaned_html_too_small", reason)
                    self.processed_status[file_key] = {
                        'status': 'skipped',
                        'reason': reason,
                        'processed_at': datetime.now().isoformat()
                    }
                    return
                
                extracted_text, extracted_metadata = self.extract_with_trafilatura(cleaned_html_content, original_url)
                
            elif self.extraction_method == 'newspaper':
                # Newspaper3k needs more HTML structure, use lighter cleaning
                lightly_cleaned_html = self.clean_html_lightly_for_newspaper(formatted_html_content)
                
                # Check if cleaning removed too much content (more lenient threshold for newspaper)
                if len(lightly_cleaned_html.strip()) < 500:
                    self.stats['skipped_files'] += 1
                    reason = f"Light HTML cleaning left too little content ({len(lightly_cleaned_html)} chars)"
                    print(f"⚠️  Skipping ({domain}): {reason}")
                    self.log_skip_reason(file_path, domain, "light_cleaned_html_too_small", reason)
                    self.processed_status[file_key] = {
                        'status': 'skipped',
                        'reason': reason,
                        'processed_at': datetime.now().isoformat()
                    }
                    return
                
                extracted_text, extracted_metadata = self.extract_with_newspaper(lightly_cleaned_html, original_url)
                cleaned_html_content = lightly_cleaned_html  # For consistency in logging and saving
                
            else:
                raise ValueError(f"Unknown extraction method: {self.extraction_method}")
            
            # Extract custom sections from original HTML (before cleaning to preserve script tags)
            from bs4 import BeautifulSoup
            soup_original = BeautifulSoup(formatted_html_content, 'html.parser')
            custom_sections = self.extract_custom_sections(soup_original, domain, original_url)
            
            # Save cleaned HTML if requested
            cleaned_html_saved = False
            full_cleaned_path = ""
            if self.save_cleaned_html:
                rel_path = os.path.relpath(file_path, CONTENT_DIR)
                cleaned_path = rel_path.replace('/raw/', '/cleaned/')
                full_cleaned_path = os.path.join(CONTENT_DIR, cleaned_path)
                
                # Create cleaned directory
                os.makedirs(os.path.dirname(full_cleaned_path), exist_ok=True)
                
                # Save cleaned HTML
                with open(full_cleaned_path, 'w', encoding='utf-8') as f:
                    f.write(cleaned_html_content)
                
                cleaned_html_saved = True
            
            # Check extraction results with detailed logging
            if not extracted_text:
                self.stats['skipped_files'] += 1
                reason = f"{self.extraction_method.capitalize()} extraction returned no text"
                print(f"⚠️  Skipping ({domain}): {reason}")
                self.log_skip_reason(file_path, domain, "extraction_failed_no_text", reason, {
                    'original_url': original_url,
                    'original_html_size': len(original_html_content),
                    'cleaned_html_size': len(cleaned_html_content),
                    'extraction_method': self.extraction_method
                })
                self.processed_status[file_key] = {
                    'status': 'skipped',
                    'reason': reason,
                    'processed_at': datetime.now().isoformat()
                }
                return
            
            extracted_text_clean = extracted_text.strip()
            if len(extracted_text_clean) < 100:
                self.stats['skipped_files'] += 1
                reason = f"{self.extraction_method.capitalize()} extracted text too short ({len(extracted_text_clean)} chars)"
                print(f"⚠️  Skipping ({domain}): {reason}")
                
                # Log first 200 chars of extracted text for debugging
                preview = extracted_text_clean[:200] + "..." if len(extracted_text_clean) > 200 else extracted_text_clean
                self.log_skip_reason(file_path, domain, "extracted_text_too_short", reason, {
                    'original_url': original_url,
                    'original_html_size': len(original_html_content),
                    'cleaned_html_size': len(cleaned_html_content),
                    'extracted_text_length': len(extracted_text_clean),
                    'extracted_text_preview': preview,
                    'extraction_method': self.extraction_method
                })
                self.processed_status[file_key] = {
                    'status': 'skipped',
                    'reason': reason,
                    'processed_at': datetime.now().isoformat()
                }
                return
            
            # Check for extraction that only contains repetitive content
            words = extracted_text_clean.split()
            unique_words = set(words)
            if len(words) > 20 and len(unique_words) / len(words) < 0.1:  # Less than 10% unique words
                self.stats['skipped_files'] += 1
                reason = f"Extracted text appears repetitive (unique word ratio: {len(unique_words)/len(words):.2%})"
                print(f"⚠️  Skipping ({domain}): {reason}")
                self.log_skip_reason(file_path, domain, "repetitive_content", reason, {
                    'original_url': original_url,
                    'total_words': len(words),
                    'unique_words': len(unique_words),
                    'unique_ratio': len(unique_words) / len(words),
                    'extraction_method': self.extraction_method
                })
                self.processed_status[file_key] = {
                    'status': 'skipped',
                    'reason': reason,
                    'processed_at': datetime.now().isoformat()
                }
                return
            
            # Clean up Markdown formatting issues
            cleaned_extracted_text = self.clean_markdown_formatting(extracted_text.strip())
            
            # Ensure proper paragraph separation
            paragraph_corrected_text = self.ensure_proper_paragraphs(cleaned_extracted_text)
            
            # Format headers in the extracted text
            markdown_content = self.format_headers_markdown(paragraph_corrected_text, cleaned_html_content)
            
            # Combine custom sections with main content
            if custom_sections:
                # Check for duplicate content to avoid repetition
                rules = self.load_domain_extraction_rules(domain)
                custom_config = rules.get('custom_content_sections', {})
                processing_options = custom_config.get('processing_options', {})
                
                if processing_options.get('skip_duplicates', True):
                    if not self.check_duplicate_content(custom_sections, markdown_content):
                        # Custom sections are unique, prepend them
                        markdown_content = custom_sections + "\n\n" + markdown_content
                else:
                    # Always add custom sections regardless of duplication
                    markdown_content = custom_sections + "\n\n" + markdown_content
            
            # Apply domain-specific text cleanup (boilerplate removal)
            markdown_content = self.text_cleaner.clean_with_domain_rules(markdown_content, domain)
            
            # Create basic metadata from extraction results
            metadata = {
                'title': '',
                'author': '',
                'date': '',
                'url': original_url
            }
            
            # Enhance with extracted metadata if available
            if extracted_metadata:
                if extracted_metadata.title:
                    metadata['title'] = extracted_metadata.title
                if extracted_metadata.author:
                    metadata['author'] = extracted_metadata.author
                if extracted_metadata.date:
                    metadata['date'] = extracted_metadata.date
            
            # Generate output paths
            rel_path = os.path.relpath(file_path, CONTENT_DIR)
            extracted_path = rel_path.replace('/raw/', '/extracted/').replace('.html', '.md')
            metadata_path = rel_path.replace('/raw/', '/metadata/').replace('.html', '.yaml')
            
            full_extracted_path = os.path.join(CONTENT_DIR, extracted_path)
            full_metadata_path = os.path.join(CONTENT_DIR, metadata_path)
            
            # Create output directories
            os.makedirs(os.path.dirname(full_extracted_path), exist_ok=True)
            os.makedirs(os.path.dirname(full_metadata_path), exist_ok=True)
            
            # Save markdown content
            with open(full_extracted_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            # Save metadata
            metadata.update({
                'extracted_at': datetime.now().isoformat(),
                'source_file': file_path,
                'markdown_file': full_extracted_path,
                'content_length': len(markdown_content),
                'extraction_method': self.extraction_method,
                'cleaned_html_saved': self.save_cleaned_html,
                'custom_sections_found': bool(custom_sections)
            })
            
            if self.save_cleaned_html:
                metadata['cleaned_html_file'] = full_cleaned_path
            
            with open(full_metadata_path, 'w', encoding='utf-8') as f:
                yaml.dump(metadata, f, default_flow_style=False, allow_unicode=True)
            
            # Update status
            status_entry = {
                'status': 'success',
                'markdown_file': full_extracted_path,
                'metadata_file': full_metadata_path,
                'content_length': len(markdown_content),
                'extraction_method': self.extraction_method,
                'processed_at': datetime.now().isoformat(),
                'custom_sections_found': bool(custom_sections)
            }
            
            if self.save_cleaned_html:
                status_entry['cleaned_html_file'] = full_cleaned_path
            
            self.processed_status[file_key] = status_entry
            
            self.stats['successful_extractions'] += 1
            
            # Create success message with optional cleaned HTML indicator
            success_msg = f"✅ Extracted ({self.extraction_method}) ({domain}): {os.path.basename(full_extracted_path)}"
            if cleaned_html_saved:
                success_msg += " 💧"  # Water drop icon to indicate cleaned HTML was saved
            if custom_sections:
                success_msg += " 📝"  # Note icon to indicate custom sections were added
            print(success_msg)
                
        except Exception as e:
            print(f"❌ Error ({domain}): {e}")
            self.stats['failed_extractions'] += 1
            
            # Log the error with more details
            self.log_skip_reason(file_path, domain, "processing_error", f"Exception during processing: {str(e)}", {
                'error_type': type(e).__name__,
                'error_message': str(e),
                'extraction_method': self.extraction_method
            })
            
            self.processed_status[file_key] = {
                'status': 'error',
                'error': str(e),
                'processed_at': datetime.now().isoformat()
            }
        
        self.stats['total_processed'] += 1

    def find_html_files(self):
        """Find all HTML files to process"""
        html_files = []
        if not os.path.exists(CONTENT_DIR):
            return html_files
        
        for root, dirs, files in os.walk(CONTENT_DIR):
            if 'raw' in root:
                for file in files:
                    if file.endswith('.html'):
                        file_path = os.path.join(root, file)
                        # Extract domain from path
                        path_parts = root.split(os.sep)
                        domain = None
                        for i, part in enumerate(path_parts):
                            if part.startswith('www.') or part.count('.') >= 1:
                                domain = part
                                break
                        
                        if domain:
                            html_files.append((file_path, domain))
        
        return html_files

    def run(self, limit=None):
        """Main processing function with optional limit"""
        start_time = time.time()
        print(f"Text Extractor started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if limit:
            print(f"Processing limit: {limit} HTML files")
        
        if self.domain_filter:
            if self.original_domain_filter != self.domain_filter:
                print(f"🌐 Domain filter: {self.original_domain_filter} -> {self.domain_filter}")
            else:
                print(f"🌐 Domain filter: {self.domain_filter}")
        
        # Find all HTML files to process
        html_files = self.find_html_files()
        if not html_files:
            print("No HTML files found to process")
            return
        
        # Apply domain filtering if specified
        if self.domain_filter:
            original_count = len(html_files)
            html_files = [(path, domain) for path, domain in html_files if domain == self.domain_filter]
            print(f"Found {original_count} total HTML files, {len(html_files)} matching domain filter")
            if not html_files:
                print(f"No HTML files found for domain: {self.domain_filter}")
                return
        else:
            print(f"Found {len(html_files)} HTML files to process")
        
        # Process each file with limit
        successfully_processed_count = 0
        for file_path, domain in html_files:
            # Check if file is already processed before counting towards limit
            file_key = f"{domain}:{file_path}"
            if file_key in self.processed_status and self.processed_status[file_key]['status'] == 'success':
                # This file is already processed, just update stats and continue
                self.stats['already_processed'] += 1
                print(f"⏭️  Already processed ({domain}): {os.path.basename(file_path)}")
                continue
            
            if limit and successfully_processed_count >= limit:
                print(f"Reached limit of {limit} HTML files")
                break
                
            # Store stats before processing
            prev_successful = self.stats['successful_extractions']
            
            # Process the file
            self.process_html_file(file_path, domain)
            
            # Only count towards limit if extraction was successful
            if self.stats['successful_extractions'] > prev_successful:
                successfully_processed_count += 1
        
        # Save status and print summary
        self.save_status()
        
        elapsed = time.time() - start_time
        print(f"\n=== Text Extractor Summary ===")
        print(f"Total files processed: {self.stats['total_processed']}")
        print(f"Successful extractions: {self.stats['successful_extractions']}")
        print(f"Failed extractions: {self.stats['failed_extractions']}")
        print(f"Already processed: {self.stats['already_processed']}")
        print(f"Skipped files: {self.stats['skipped_files']}")
        print(f"Total time: {elapsed:.2f} seconds")
        
        # Write summary to log
        self.write_summary_log(elapsed)

    def write_summary_log(self, elapsed_time):
        """Write processing summary to log file"""
        now = datetime.now()
        month_str = now.strftime("%Y-%m")
        month_dir = os.path.join(LOGS_DIR, month_str)
        os.makedirs(month_dir, exist_ok=True)
        
        summary_log_path = os.path.join(month_dir, "text_extractor_summary.log")
        
        # Calculate skip reasons breakdown
        skip_reasons = {}
        for file_key, status in self.processed_status.items():
            if status.get('status') in ['skipped', 'error']:
                reason = status.get('reason', 'unknown')
                skip_type = 'error' if status.get('status') == 'error' else 'skipped'
                skip_reasons[f"{skip_type}:{reason}"] = skip_reasons.get(f"{skip_type}:{reason}", 0) + 1
        
        log_entry = (
            f"{now.strftime('%Y-%m-%d %H:%M:%S')} | "
            f"Processed: {self.stats['total_processed']} | "
            f"Extracted: {self.stats['successful_extractions']} | "
            f"Failed: {self.stats['failed_extractions']} | "
            f"Skipped: {self.stats['skipped_files']} | "
            f"Already processed: {self.stats['already_processed']} | "
            f"Time: {elapsed_time:.2f}s"
        )
        
        if skip_reasons:
            skip_details = " | Skip reasons: " + ", ".join([f"{reason}({count})" for reason, count in skip_reasons.items()])
            log_entry += skip_details
        
        log_entry += "\n"
        
        with open(summary_log_path, "a", encoding="utf-8") as f:
            f.write(log_entry)

if __name__ == "__main__":
    import sys
    import time
    
    # Parse command line arguments
    limit = None
    extraction_method = 'trafilatura'  # Default
    save_cleaned_html = False  # Default
    domain_filter = None  # Default
    
    if len(sys.argv) > 1:
        # Check for help flag first
        if sys.argv[1] in ['--help', '-h']:
            print("Text Extractor Script - Extracts clean article text from HTML files")
            print("")
            print("Usage: python text_extractor.py [LIMIT] [METHOD] [--save-cleaned-html] [--domain DOMAIN]")
            print("")
            print("Parameters:")
            print("  LIMIT              (optional): Number of HTML files to process (leave empty for all)")
            print("  METHOD             (optional): 'trafilatura' (default) or 'newspaper'")
            print("  --save-cleaned-html (optional): Save cleaned HTML files alongside original files")
            print("  --domain DOMAIN    (optional): Only process files from specified domain (e.g., digi24.ro, bzi.ro, www.digi24.ro)")
            print("")
            print("Examples:")
            print("  python text_extractor.py                                         # Process all files with trafilatura")
            print("  python text_extractor.py 10                                      # Process 10 files with trafilatura")
            print("  python text_extractor.py 5 newspaper                             # Process 5 files with newspaper")
            print("  python text_extractor.py 10 trafilatura --save-cleaned-html      # Process 10 files and save cleaned HTML")
            print("  python text_extractor.py \"\" newspaper --save-cleaned-html        # Process all files with newspaper and save cleaned HTML")
            print("  python text_extractor.py 5 trafilatura --domain digi24.ro       # Process 5 files from digi24.ro only")
            print("  python text_extractor.py 2 --domain bzi.ro                       # Process 2 files from bzi.ro only")
            sys.exit(0)
        
        try:
            limit = int(sys.argv[1])
            if limit <= 0:
                print("Error: Limit must be a positive integer")
                sys.exit(1)
        except ValueError:
            print("Error: Invalid limit value. Must be an integer.")
            sys.exit(1)
    
    # Parse remaining arguments
    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]
        
        if arg == '--save-cleaned-html':
            save_cleaned_html = True
            print("💧 Cleaned HTML will be saved alongside extraction results")
        elif arg == '--domain':
            if i + 1 < len(sys.argv):
                domain_filter = sys.argv[i + 1]
                i += 1  # Skip the domain value
            else:
                print("Error: --domain requires a domain value")
                sys.exit(1)
        elif arg.lower() in ['trafilatura', 'newspaper']:
            extraction_method = arg.lower()
        else:
            print(f"Error: Unknown argument '{arg}'")
            print("Usage: python text_extractor.py [limit] [method] [--save-cleaned-html] [--domain DOMAIN]")
            sys.exit(1)
        
        i += 1
    
    print(f"Using extraction method: {extraction_method}")
    extractor = TextExtractor(extraction_method=extraction_method, save_cleaned_html=save_cleaned_html, domain_filter=domain_filter)
    extractor.run(limit)