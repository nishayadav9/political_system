# core/templatetags/translation_tags.py
from django import template

register = template.Library()

class TrackNode(template.Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        return self.nodelist.render(context)

@register.tag(name="track")
def do_track(parser, token):
    nodelist = parser.parse(('endtrack',))
    parser.delete_first_token()
    return TrackNode(nodelist)
