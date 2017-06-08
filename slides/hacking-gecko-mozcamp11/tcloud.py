#!/usr/bin/python

import fileinput
import random

print """
<html>
<head>
<style>
span.cloud { margin: 5px 10px 0px 10px; opacity: 0.0;}
span.cloud0 { font-size: 0.5em; }
span.cloud1 { font-size: 0.7em; }
span.cloud2 { font-size: 1.0em; }
span.cloud3 { font-size: 1.3em; }
span.cloud4 { font-size: 1.6em; }
span.cloud5 { font-size: 1.9em; }
span.cloud6 { font-size: 2.2em; }
span.cloud7 { font-size: 2.5em; }
span.cloud8 { font-size: 2.8em; }
span.cloud9 { font-size: 3.1em; }
span.cloud10 { font-size: 3.4em; }
</style>
<script type="application/javascript">
window.currtag = 0;
function displaynext() {
  document.getElementById('tc-tag' + window.currtag++).style.opacity = 1.0;
}
</script>
</head>
<body>
<section>
"""

lines = []
for line in fileinput.input():
  index = fileinput.lineno() - 1
  size = random.randint(3,10) if index <= 20 else random.randint(0,7)
  lines.append({'index': index, 'text': line.rstrip(), 'size': size})

random.shuffle(lines)

for line in lines:
  print '<span id="tc-tag%d" class="cloud cloud%d">%s</span>' % (line['index'], line['size'], line['text'])

print """
</section>
<br><br>
<button onclick="displaynext();">Click Me!</button>
</body>
</html>"""
