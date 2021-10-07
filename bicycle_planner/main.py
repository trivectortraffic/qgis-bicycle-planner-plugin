def classFactory(iface):
    print('classFactory')
    from .plugin import Plugin

    return Plugin(iface)
