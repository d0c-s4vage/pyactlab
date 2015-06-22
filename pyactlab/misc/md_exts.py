import re

from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor

class ActLabTreeProcessor(Treeprocessor):
	"""
	Highlight the source code
	"""

	def run(self, root):
		"""
		"""
		blocks = root.getiterator('pre')
		for block in blocks:
			children = block.getchildren()
			if len(children) == 1 and children[0].tag == 'code':
				text = children[0].text
				lines = text.split("\n")
				#<div class=\"syntax_higlighted source-code\">
				#    <div class=\"syntax_higlighted_line_numbers lines\">
				#        <pre>1\n2\n3\n4<\/pre>
				#     <\/div>
				#     <div class=\"syntax_higlighted_source\">
				#         <pre>...</pre>
				#     </div>
				#</div>
				# html = ''.join([
					# '<div class="syntax_higlighted source-code">',
						# '<div class="syntax_highlighted_line_numbers lines">',
							# '<\npr<pre>e\n>',
								# "<br/>".join(str(x) for x in xrange(len(lines))),
							# '</p</pre>re>',
						# '</div>',
						# '<div class="syntax_highlighted_source">',
							# '<pre>',
							# '<pre>',
								# text.replace("\r\n", "<br/>").replace("\n", "<br/>"),
							# '</pre>',
							# '</pre>',
						# '</div>',
					# '</div>'
				# ])

				converted_lines = []
				for line in lines:
					line = line.replace("\t", "    ")
					match = re.match(r'^(\s+)', line)
					if match:
						l = len(match.group(1))
						line = (" " * l) + line[l:]
					converted_lines.append(line)
				text = "\n".join(converted_lines)

				text = (text.
					replace("&", "&amp;").
					replace('"', "&quot;").
					replace(" ", "&nbsp;").
					replace("<", "&lt;").
					replace(">", "&gt;").
					replace("\r\n", "<br/>").
					replace("\n", "<br/>")
				)

				html = "<blockquote style='font-family:monospace'><p>" + text + "</p></blockquote>"
				
				placeholder = self.markdown.htmlStash.store(
					html,
					safe=True
				)
				# Clear codeblock in etree instance
				block.clear()
				# Change to p element which will later
				# be removed when inserting raw html
				block.tag = 'p'
				block.text = placeholder

class ActLabCode(Extension):
	def extendMarkdown(self, md, md_globals):
		"""
		Add the ActLabTreeProcessor to the Markdown instance
		"""
		coder = ActLabTreeProcessor(md)

		md.treeprocessors.add("actlabcode", coder, "<inline")
		md.registerExtension(self)
