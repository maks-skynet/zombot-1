# coding=utf-8
import logging
from game_state.game_types import GameWoodGrave, GameWoodGraveDouble,\
    GamePickItem, GameWoodTree, GameGainItem, GamePickup
from game_state.game_event import dict2obj
from game_actors_and_handlers.base import BaseActor

logger = logging.getLogger(__name__)


class WoodTargetSelecter(BaseActor):

    def perform_action(self):
        # get all free workers
        wood_graves = self._get_game_location().get_all_objects_by_types([
            GameWoodGrave.type,
            GameWoodGraveDouble.type
        ])
        # get free workers
        free_workers = []
        for wood_grave in wood_graves:
            if not self._get_player_brains().is_busy(wood_grave):
                free_workers.append(wood_grave)
        # get any free worker
        if free_workers:
            free_worker = free_workers[0]
            # check brains count
            if self._get_player_brains().has_sufficient_brains_count(
                                                                free_worker):
                logger.info("Отправляем зомби на работу")
                # select any wood tree
                trees = self._get_game_location().get_all_objects_by_type(
                    GameWoodTree.type
                )
                if trees:
                    tree = trees[0]
                    # make sure gain is not started yet
                    if tree.gainStarted:
                        logger.info("Уже рубится")
                    else:
                        logger.info("Рубим дерево")
                        gain_event = GameGainItem(tree.id, free_worker.id)
                        self._get_events_sender().send_game_events(
                                                            [gain_event])
                else:
                    logger.info("Не осталось деревьев")


class WoodPicker(BaseActor):

    def perform_action(self):
        wood_graves = self._get_game_location().get_all_objects_by_type(
                            GameWoodGrave.type)
        wood_graves += self._get_game_location().get_all_objects_by_type(
                            GameWoodGraveDouble.type)
        for wood_grave in wood_graves:
            for material_id in list(wood_grave.materials):
                material = self._get_item_reader().get(material_id)
                name = material.name
                logger.info(u'Подбираем ' + name)
                self._pick_material(wood_grave, material.id)
                # update game state
                wood_grave.materials.remove(material_id)

    def _pick_material(self, wood_grave, material_id):
        pick_item = GamePickItem(itemId=material_id, objId=wood_grave.id)
        self._get_events_sender().send_game_events([pick_item])


class GainMaterialEventHandler(object):

    def __init__(self, item_reader, game_location,
                  timer):
        self.__item_reader = item_reader
        self.__game_location = game_location
        self.__timer = timer

    def _get_timer(self):
        return self.__timer

    def get_game_loc(self):
        return self.__game_location

    def handle(self, event_to_handle):
        gameObject = self.__game_location.get_object_by_id(
            event_to_handle.objId
        )
        self.updateJobDone(gameObject)
        if event_to_handle.action == 'start':
            logger.info("Начата работа" + '. jobEndTime:'
                        + str(event_to_handle.jobEndTime) +
                        ', current time:' +
                        str(self._get_timer()._get_current_client_time()))
            gameObject.target = dict2obj({'id': event_to_handle.targetId})
            gameObject.jobStartTime = event_to_handle.jobStartTime
            gameObject.jobEndTime = event_to_handle.jobEndTime
        elif event_to_handle.action == 'stop':
            logger.info("Окончена работа")

    def updateJobDone(self, wood_grave):
        if hasattr(wood_grave, 'jobEndTime'):
            logger.info('jobEndTime:' + wood_grave.jobEndTime +
                        ', current time:' +
                        str(self._get_timer()._get_current_client_time()))
            if (self._get_timer().has_elapsed(wood_grave.jobEndTime)):
                if hasattr(wood_grave, 'target'):
                    target_id = wood_grave.target.id
                    target = self.get_game_loc().get_object_by_id(target_id)
                    target.materialCount -= 1
                    target_item = self.__item_reader.get(target.item)
                    logger.info("Материал добыт")
                    wood_grave.materials.append(target_item.material)
                    if target.materialCount == 0:
                        logger.info("Ресурсы исчерпаны!")
                        box_item = self.__item_reader.get(target_item.box)
                        new_obj = dict2obj({'item': '@' + box_item.id,
                                            'type': GamePickup.type,
                                            'id': target_id})
                        self.get_game_loc().remove_object_by_id(target_id)
                        self.get_game_loc().append_object(new_obj)
                        logger.info(u"'%s' превращён в '%s'" %
                                    (target_item.name, box_item.name))
                        # add free brains
                        delattr(wood_grave, 'target')
                delattr(wood_grave, 'jobEndTime')
        else:
            logger.info("There's no jobEndTime")
