server_config = dict(
    # relative path to the uploaded liferea.db
    DATABASEPATH='share/liferea.db',
    # flask debug flag
    DEBUG=True,
    # flask secret key
    SECRET_KEY='development key',
    # name of the user
    USERNAME='myusername',
    # password of the user
    PASSWORD='mypassword',
    # items on a page
    ITEMS_PER_PAGE=15,
    # host on which the flask-app should bind to
    # use 127.0.0.1 if you use webferea through a webserver proxy
    # use 0.0.0.0 if you want to use webferea without a webserver (not recommended)
    HOST="127.0.0.1",
    # port on which the flask-app should bind to
    PORT=5665,
    # name of the feeds who should be shown in webferea
    # that is the title you can edit in liferea (<title> tag)
    #NODES = ("Wikipedia featured articles feed", "Science Latest")
    NODES = ()
)
