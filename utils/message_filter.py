from uuid import UUID


def is_from_request_with_id(response: dict, id: UUID):
    response_id = response.get("id")
    return response_id is not None or UUID(response_id) != id


def is_new_player_online_event(response: dict) -> bool:
    return response.get("event") == "newUserOnline"

def is_player_go_offline_event(response: dict) -> bool:
    return response.get("event") == "userOffline"

def is_new_challenger_event(response: dict) -> bool:
    return response.get("event") == "userOffline"
