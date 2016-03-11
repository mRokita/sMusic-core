class IncompatibleVersions(Exception):
    def __init__(self, msg):
        super(IncompatibleVersions, self).__init__(msg)


EXCEPTIONS = {
    u"incompatibleVersions": IncompatibleVersions
}