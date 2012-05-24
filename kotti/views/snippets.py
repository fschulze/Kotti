from kotti.resources import Document

class Children(object):
    """
    Snippet view rendering list of child nodes.

    Parameter 'class' sets a CSS-class on the list.
    """
    def __init__(self, request):
        self.request = request
    def __call__(self):
        list_class = self.request.GET.get('class')
        return {
            'list_class': list_class,
        }

def includeme(config):
    config.add_snippet(
        Children,
        name = 'children',
        context = Document,
        renderer='kotti:templates/snippet/children.pt',
    )