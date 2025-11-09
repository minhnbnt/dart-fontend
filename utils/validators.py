"""
Validation utility functions for user input
"""


def validate_username(username: str) -> tuple[bool, str]:
    """
    Validate username format and requirements.

    Args:
        username: The username to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    username = username.strip()

    if not username:
        return False, "Username không được để trống!"

    if len(username) < 3:
        return False, "Username phải có ít nhất 3 ký tự!"

    if len(username) > 20:
        return False, "Username không được vượt quá 20 ký tự!"

    # Check if username contains only alphanumeric and underscore
    if not username.replace("_", "").isalnum():
        return False, "Username chỉ được chứa chữ cái, số và dấu gạch dưới!"

    # Check if username starts with a letter or number
    if not username[0].isalnum():
        return False, "Username phải bắt đầu bằng chữ cái hoặc số!"

    return True, ""


def validate_password(password: str) -> tuple[bool, str]:
    """
    Validate password format and requirements.

    Args:
        password: The password to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not password:
        return False, "Password không được để trống!"

    if len(password) < 6:
        return False, "Password phải có ít nhất 6 ký tự!"

    if len(password) > 50:
        return False, "Password không được vượt quá 50 ký tự!"

    return True, ""


def validate_password_match(password: str, confirm_password: str) -> tuple[bool, str]:
    """
    Validate that password and confirmation match.

    Args:
        password: The password
        confirm_password: The confirmation password

    Returns:
        Tuple of (is_valid, error_message)
    """
    if password != confirm_password:
        return False, "Password và xác nhận password không khớp!"

    return True, ""


def translate_error_message(error: str) -> str:
    """
    Translate common error messages from English to Vietnamese.

    Args:
        error: The error message to translate

    Returns:
        Translated error message
    """
    error_lower = error.lower()

    # Login/Register errors
    if "does not match" in error_lower or "incorrect" in error_lower:
        return "Username hoặc password không đúng!"

    if "not found" in error_lower:
        return "Tài khoản không tồn tại!"

    if "already exists" in error_lower:
        return "Username đã tồn tại! Vui lòng chọn username khác."

    if "other session" in error_lower or "already logged" in error_lower:
        return "Tài khoản đang đăng nhập ở nơi khác!"

    if "invalid" in error_lower:
        return "Thông tin không hợp lệ!"

    # Connection errors
    if "connection" in error_lower or "timeout" in error_lower:
        return "Lỗi kết nối đến server!"

    if "network" in error_lower:
        return "Lỗi mạng! Vui lòng kiểm tra kết nối."

    # Default: return original message
    return error
