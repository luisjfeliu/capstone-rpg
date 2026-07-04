# behave environment hooks


def before_scenario(context, scenario):
    context.game_state = None
