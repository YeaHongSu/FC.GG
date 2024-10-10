def scale_value(value, min_value=0, max_value=100):
    return (value - min_value) / (max_value - min_value)

class MetaScoreCalculator:
    def __init__(self, player):
        self.goals = scale_value(float(player['득점'].split('(')[0]))
        self.assists = scale_value(float(player['도움'].split('(')[0]))
        self.shots_on_target = scale_value(float(player['유효 슛'].split('(')[0]))
        self.pass_success_rate = scale_value(float(player['패스 성공률'].split('%')[0]))
        self.dribble_success_rate = scale_value(float(player['드리블 성공률'].split('%')[0]))
        self.tackle_success_rate = scale_value(float(player['태클 성공률'].split('%')[0]))
        self.interception_success_rate = scale_value(float(player['차단 성공률'].split('%')[0]))
        self.interception = scale_value(float(player['가로채기'].split('(')[0]))
        self.aerial_success_rate = scale_value(float(player['공중볼 경합 성공률'].split('%')[0]))

    def calculate_score(self):
        # Default meta score calculation
        raise NotImplementedError("This method should be overridden by subclasses")


class ST_MetaScore(MetaScoreCalculator):
    def calculate_score(self):
        goal_contribution = (self.goals + self.shots_on_target) * 3
        attack_contribution = (self.assists + self.pass_success_rate + self.dribble_success_rate) * 1
        defense_contribution = (self.tackle_success_rate + self.interception_success_rate + self.aerial_success_rate) * 0.5
        
        return goal_contribution + attack_contribution + defense_contribution

class CF_MetaScore(MetaScoreCalculator):
    def calculate_score(self):
        scoring_contribution = (self.goals + self.shots_on_target) * 2.5
        attack_contribution = (self.assists + self.pass_success_rate + self.dribble_success_rate) * 1.5
        defense_contribution = (self.tackle_success_rate + self.interception_success_rate + self.aerial_success_rate) * 0.5

        return scoring_contribution + attack_contribution + defense_contribution

class LW_MetaScore(MetaScoreCalculator):
    def calculate_score(self):
        attack_contribution = (self.goals + self.shots_on_target + self.assists) * 2.5
        passing_and_dribbling = (self.pass_success_rate + self.dribble_success_rate) * 2
        defense_contribution = (self.tackle_success_rate + self.interception_success_rate + self.aerial_success_rate) * 1

        return attack_contribution + passing_and_dribbling + defense_contribution

class RW_MetaScore(MetaScoreCalculator):
    def calculate_score(self):
        attack_contribution = (self.goals + self.shots_on_target + self.assists) * 2.5
        passing_and_dribbling = (self.pass_success_rate + self.dribble_success_rate) * 2
        defense_contribution = (self.tackle_success_rate + self.interception_success_rate + self.aerial_success_rate) * 1

        return attack_contribution + passing_and_dribbling + defense_contribution

class CAM_MetaScore(MetaScoreCalculator):
    def calculate_score(self):
        attack_contribution = (self.goals + self.shots_on_target + self.assists) * 2.5
        creativity_and_passing = (self.pass_success_rate + self.dribble_success_rate) * 2
        defense_contribution = (self.tackle_success_rate + self.interception_success_rate) * 0.5

        return attack_contribution + creativity_and_passing + defense_contribution

class CM_MetaScore(MetaScoreCalculator):
    def calculate_score(self):
        attack_contribution = (self.goals + self.shots_on_target) * 1
        defense_contribution = (self.tackle_success_rate + self.interception_success_rate + self.interception) * 2
        linking_play = self.pass_success_rate * 2
        assist_attempts = self.assists * 1.5

        return attack_contribution + defense_contribution + linking_play + assist_attempts

class CDM_MetaScore(MetaScoreCalculator):
    def calculate_score(self):
        defense_contribution = (self.tackle_success_rate + self.interception_success_rate + self.interception) * 2
        linking_play = self.pass_success_rate * 1.5
        assist_attempts = (self.assists + self.shots_on_target) * 1
        attack_contribution = self.goals * 0.5

        return defense_contribution + linking_play + assist_attempts + attack_contribution

class CB_MetaScore(MetaScoreCalculator):
    def calculate_score(self):
        defense_contribution = (self.tackle_success_rate + self.interception_success_rate + self.interception + self.aerial_success_rate) * 3
        passing_ability = (self.pass_success_rate + self.assists) * 1
        attack_contribution = (self.goals + self.shots_on_target) * 0.5

        return defense_contribution + passing_ability + attack_contribution

class LB_MetaScore(MetaScoreCalculator):
    def calculate_score(self):
        defense_contribution = (self.tackle_success_rate + self.interception_success_rate + self.interception) * 2
        aerial_duel_contribution = self.aerial_success_rate * 1
        attack_support = (self.assists + self.pass_success_rate + self.dribble_success_rate) * 1.5
        attack_contribution = (self.goals + self.shots_on_target) * 0.5

        return defense_contribution + aerial_duel_contribution + attack_support + attack_contribution

class RB_MetaScore(MetaScoreCalculator):
    def calculate_score(self):
        defense_contribution = (self.tackle_success_rate + self.interception_success_rate + self.interception) * 2
        aerial_duel_contribution = self.aerial_success_rate * 1
        attack_support = (self.assists + self.pass_success_rate + self.dribble_success_rate) * 1.5
        attack_contribution = (self.goals + self.shots_on_target) * 0.5

        return defense_contribution + aerial_duel_contribution + attack_support + attack_contribution

class GK_MetaScore(MetaScoreCalculator):
    def __init__(self, player):
        self.saves = scale_value(float(player['선방(골 차단)'].split('(')[0]))
        self.pass_success_rate = scale_value(float(player['패스 성공률'].split('%')[0]))
        self.tackle_success_rate = scale_value(float(player['태클 성공률'].split('%')[0]))
        self.interception = scale_value(float(player['가로채기'].split('(')[0]))

    def calculate_score(self):
        save_ability = self.saves * 3
        defense_contribution = (self.tackle_success_rate + self.interception) * 1
        passing_ability = self.pass_success_rate * 1.5

        return save_ability + defense_contribution + passing_ability


def get_meta_score(player, position):
    if position == 'ST':
        return ST_MetaScore(player).calculate_score()
    elif position == 'CF':
        return CF_MetaScore(player).calculate_score()
    elif position == 'LW':
        return LW_MetaScore(player).calculate_score()
    elif position == 'RW':
        return RW_MetaScore(player).calculate_score()
    elif position == 'CAM':
        return CAM_MetaScore(player).calculate_score()
    elif position == 'CM':
        return CM_MetaScore(player).calculate_score()
    elif position == 'CDM':
        return CDM_MetaScore(player).calculate_score()
    elif position == 'CB':
        return CB_MetaScore(player).calculate_score()
    elif position == 'LB':
        return LB_MetaScore(player).calculate_score()
    elif position == 'RB':
        return RB_MetaScore(player).calculate_score()
    elif position == 'GK':
        return GK_MetaScore(player).calculate_score()
