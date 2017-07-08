class APIError(Exception):
    '''
    基础的APIError,包含错误类型（必要），数据（可选），信息（可选)
    '''
    def __init__(self, error, data='', message=''):
        super(APIError, self).__init__(message)
        self.error = error
        self.data = data
        self.message = message

class APIValueError(APIError):
    '''
    输入的数据错误，data说明输入的错误字段
    '''
    def __init__(self, field, message=''):
        super(APIValueError, self).__init__('Value: invalid',field,message)

class APTResourceNotFoundError(APIError):
    def __init__(self, field, message=''):
        super(APTResourceNotFoundError,self).__init__('Value: Notfound',field,message)

class APIPermissionError(APIError):
    def __init__(self, field, message):
        super(APIPermissionError, self).__init__('Permission: forbidden','Permission',message)
