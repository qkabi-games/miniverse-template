class_name __Project__
extends Game

#region Overrides
func _ready() -> void:
    starting.connect(_on_restarting)
    stopping.connect(_on_reviving)
    reviving.connect(_on_stopping)
    restarting.connect(_on_starting)


func _create_pre_game_overlay() -> PreGameOverlay:
    # Todo: Implement
    return null


func _create_mid_game_overlay() -> MidGameOverlay:
    # Todo: Implement
    return null


func _create_end_game_overlay() -> EndGameOverlay:
    # Todo: Implement
    return null


func _get_record() -> Record:
    return Record.new()
#endregion


#region Callbacks
func _on_starting(data: Object) -> void:
    # Todo: Implement
    acknowledge_request(data)


func _on_stopping(data: Object) -> void:
    # Todo: Implement
    acknowledge_request(data)


func _on_reviving(data: Object) -> void:
    # Todo: Implement
    acknowledge_request(data)


func _on_restarting(data: Object) -> void:
    # Todo: Implement
    acknowledge_request(data)
#endregion
