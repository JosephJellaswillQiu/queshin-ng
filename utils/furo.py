"""识别是否可以副露，根据副录类型返回可能的附录组合
Args:
        hand (list[num]): A list of tiles representing the hand. 0~8 are manzu, 9~17 are pinzu, 18~26 are souzu, 27~33 are honors.
        furo (list[list[num]]): A list of melds.
        card (num): last played card
        
Returns:
        possible hand(list[num]) and furo(list[list[num]]) pair:

"""
