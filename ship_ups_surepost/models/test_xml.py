from xml.etree.ElementTree import Element, SubElement, tostring

root = Element('root')
child = SubElement(root, "child")
child.text = "I am a child"

print tostring(root)
