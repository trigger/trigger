
# triggerdocs.py - Custom docs extension for Sphinx

def setup(app):
    # Create a :setting: cross-ref to link to configuration options
    app.add_crossref_type(
        directivename='setting',
        rolename='setting',
        indextemplate='pair: %s; setting',
    )
