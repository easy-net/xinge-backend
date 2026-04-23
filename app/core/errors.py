class AppError(Exception):
    def __init__(self, status_code: int, code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


class ValidationError(AppError):
    def __init__(self, message: str = "invalid request", code: int = 1001):
        super().__init__(400, code, message)


class AuthError(AppError):
    def __init__(self, message: str = "unauthorized", code: int = 2001):
        super().__init__(401, code, message)


class ForbiddenError(AppError):
    def __init__(self, message: str = "forbidden", code: int = 2003):
        super().__init__(403, code, message)


class NotFoundError(AppError):
    def __init__(self, message: str = "not found", code: int = 4004):
        super().__init__(404, code, message)


class ConflictError(AppError):
    def __init__(self, message: str = "conflict", code: int = 4009):
        super().__init__(409, code, message)

