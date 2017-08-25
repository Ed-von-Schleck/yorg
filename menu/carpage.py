from itertools import product
from yaml import load
from panda3d.core import TextNode
from direct.gui.DirectButton import DirectButton
from direct.gui.DirectGuiGlobals import DISABLED, NORMAL
from direct.gui.OnscreenText import OnscreenText
from yyagl.engine.gui.page import Page, PageFacade
from yyagl.engine.network.server import Server
from yyagl.engine.gui.imgbtn import ImgBtn
from yyagl.engine.network.client import Client
from yyagl.racing.season.season import SingleRaceSeason
from yyagl.gameobject import GameObject
from .netmsgs import NetMsgs
from .driverpage import DriverPage, DriverPageProps
from .thankspage import ThanksPageGui


class CarPageProps(object):

    def __init__(self, cars, car_path, phys_path, player_name, drivers_img,
                 cars_img, drivers):
        self.cars = cars
        self.car_path = car_path
        self.phys_path = phys_path
        self.player_name = player_name
        self.drivers_img = drivers_img
        self.cars_img = cars_img
        self.drivers = drivers


class CarPageGui(ThanksPageGui):

    def __init__(self, mdt, menu, carpage_props):
        self.car = None
        self.current_cars = None
        self.track_path = None
        self.props = carpage_props
        ThanksPageGui.__init__(self, mdt, menu)

    def bld_page(self):
        menu_gui = self.mdt.menu.gui
        if game.logic.curr_cars:
            self.props.cars = game.logic.curr_cars
        self.pagewidgets = [OnscreenText(
            text=_('Select the car'), pos=(0, .8),
            **menu_gui.menu_args.text_args)]
        self.track_path = self.mdt.menu.track  # we should pass it
        t_a = self.mdt.menu.gui.menu_args.text_args.copy()
        del t_a['scale']
        cars_per_row = 4
        for row, col in product(range(2), range(cars_per_row)):
            if row * cars_per_row + col >= len(self.props.cars):
                break
            z_offset = 0 if len(self.props.cars) > cars_per_row else .35
            num_car = len(self.props.cars) - cars_per_row if row == 1 else \
                min(cars_per_row, len(self.props.cars))
            x_offset = .4 * (cars_per_row - num_car)
            self.pagewidgets += [ImgBtn(
                scale=.32,
                pos=(-1.2 + col * .8 + x_offset, 1, .4 - z_offset - row * .7),
                frameColor=(0, 0, 0, 0),
                image=self.props.car_path % self.props.cars[col + row * cars_per_row],
                command=self.on_car,
                extraArgs=[self.props.cars[col + row * cars_per_row]],
                **self.mdt.menu.gui.menu_args.imgbtn_args)]
            self.pagewidgets += [OnscreenText(
                self.props.cars[col + row * cars_per_row],
                pos=(-1.2 + col * .8 + x_offset, .64 - z_offset - row * .7),
                scale=.072, **t_a)]
            cpath = self.props.phys_path % self.props.cars[col + row * cars_per_row]
            with open(cpath) as phys_file:
                cfg = load(phys_file)
            speed = cfg['max_speed'] / 140.0
            fric = cfg['friction_slip'] / 3.0
            roll = cfg['roll_influence'] / .2
            speed = int(round((speed - 1) * 100))
            fric = int(round((fric - 1) * 100))
            roll = -int(round((roll - 1) * 100))
            sign = lambda x: '\1green\1+\2' if x > 0 else ''
            psign = lambda x, sgn=sign: '+' if x == 0 else sgn(x)
            __col_ = lambda x: '\1green\1%s\2' if x > 0 else '\1red\1%s\2'
            _col_ = lambda x, __col=__col_: __col(x) % x
            pcol = lambda x, _col=_col_: x if x == 0 else _col(x)

            def add_txt(txt, val, pos_z, psign=psign, pcol=pcol, col=col,
                        x_offset=x_offset, z_offset=z_offset, row=row):
                self.pagewidgets += [OnscreenText(
                    '%s: %s%s%%' % (txt, psign(val), pcol(val)),
                    pos=(-.9 + col * .8 + x_offset,
                         pos_z - z_offset - row * .7),
                    scale=.052, align=TextNode.A_right, **t_a)]
            txt_lst = [(_('adherence'), fric, .11), (_('speed'), speed, .27),
                       (_('stability'), roll, .19)]
            map(lambda txt_def: add_txt(*txt_def), txt_lst)
        map(self.add_widget, self.pagewidgets)
        self.current_cars = {}
        ThanksPageGui.bld_page(self)

    def _buttons(self, car):
        is_btn = lambda wdg: wdg.__class__ == DirectButton
        buttons = [wdg for wdg in self.widgets if is_btn(wdg)]
        return [btn for btn in buttons if btn['extraArgs'] == [car]]

    def on_car(self, car):
        self.mdt.menu.gui.notify('on_car_selected', car)
        driverpage_props = DriverPageProps(
            self.props.player_name, self.props.drivers_img,
            self.props.cars_img, self.props.cars, self.props.drivers)
        drv_page = DriverPage(self.mdt.menu.gui.menu_args, self.track_path,
                              car, driverpage_props, self.mdt.menu)
        self.mdt.menu.push_page(drv_page)


class CarPageGuiSeason(CarPageGui):

    def on_car(self, car):
        self.mdt.menu.gui.notify('on_car_selected_season', car)
        driverpage_props = DriverPageProps(
            self.props.player_name, self.props.drivers_img,
            self.props.cars_img, self.props.cars, self.props.drivers)
        drv_page = DriverPage(self.mdt.menu.gui.menu_args, self.track_path,
                              car, driverpage_props, self.mdt.menu)
        self.mdt.menu.push_page(drv_page)


class CarPageGuiServer(CarPageGui):

    def bld_page(self):
        CarPageGui.bld_page(self)
        eng.register_server_cb(self.process_srv)
        eng.car_mapping = {}

    def on_car(self, car):
        eng.log('car selected: ' + car)
        Server().send([NetMsgs.car_selection, car])
        for btn in self._buttons(car):
            btn['state'] = DISABLED
            btn.setAlphaScale(.25)
        if self in self.current_cars:
            curr_car = self.current_cars[self]
            eng.log('car deselected: ' + curr_car)
            Server().send([NetMsgs.car_deselection, curr_car])
            for btn in self._buttons(curr_car):
                btn['state'] = NORMAL
                btn.setAlphaScale(1)
        self.current_cars[self] = car
        eng.car_mapping['self'] = car
        self.evaluate_starting()

    def evaluate_starting(self):
        connections = eng.connections + [self]
        if all(conn in self.current_cars for conn in connections):
            packet = [NetMsgs.start_race, len(self.current_cars)]

            def process(k):
                '''Processes a car.'''
                return 'server' if k == self else k.getAddress().getIpString()
            for k, val in self.current_cars.items():
                packet += [process(k), val]
            Server().send(packet)
            eng.log('start race: ' + str(packet))
            curr_car = self.current_cars[self]
            # manage as event
            game.logic.season = SingleRaceSeason()
            game.fsm.demand('Race', self.track_path, curr_car, packet[2:])

    def process_srv(self, data_lst, sender):
        if data_lst[0] == NetMsgs.car_request:
            car = data_lst[1]
            eng.log('car requested: ' + car)
            btn = self._buttons(car)[0]
            if btn['state'] == DISABLED:
                Server().send([NetMsgs.car_deny], sender)
                eng.log('car already selected: ' + car)
            elif btn['state'] == NORMAL:
                eng.log('car selected: ' + car)
                if sender in self.current_cars:
                    _btn = self._buttons(self.current_cars[sender])[0]
                    _btn['state'] = NORMAL
                    _btn.setAlphaScale(1)
                self.current_cars[sender] = car
                btn['state'] = DISABLED
                btn.setAlphaScale(.25)
                Server().send([NetMsgs.car_confirm, car], sender)
                Server().send([NetMsgs.car_selection, car])
                eng.car_mapping[sender] = car
                self.evaluate_starting()


class CarPageGuiClient(CarPageGui):

    def bld_page(self):
        CarPageGui.bld_page(self)
        eng.register_client_cb(self.process_client)

    def on_car(self, car):
        eng.log('car request: ' + car)
        Client().send([NetMsgs.car_request, car])

    def process_client(self, data_lst, sender):
        if data_lst[0] == NetMsgs.car_confirm:
            if self.car:
                _btn = self._buttons(self.car)[0]
                _btn['state'] = NORMAL
                _btn.setAlphaScale(1)
            self.car = car = data_lst[1]
            eng.log('car confirmed: ' + car)
            btn = self._buttons(car)[0]
            btn['state'] = DISABLED
            btn.setAlphaScale(.25)
        if data_lst[0] == NetMsgs.car_deny:
            eng.log('car denied')
        if data_lst[0] == NetMsgs.car_selection:
            car = data_lst[1]
            eng.log('car selection: ' + car)
            btn = self._buttons(car)[0]
            btn['state'] = DISABLED
            btn.setAlphaScale(.25)
        if data_lst[0] == NetMsgs.car_deselection:
            car = data_lst[1]
            eng.log('car deselection: ' + car)
            btn = self._buttons(car)[0]
            btn['state'] = NORMAL
            btn.setAlphaScale(1)
        if data_lst[0] == NetMsgs.start_race:
            eng.log('start_race: ' + str(data_lst))
            # manage as event
            game.logic.season = SingleRaceSeason()
            game.fsm.demand('Race', self.track_path, self.car, data_lst[2:])


class CarPage(Page):
    gui_cls = CarPageGui

    def __init__(self, menu_args, carpage_props, menu):
        self.menu_args = menu_args
        self.menu = menu
        init_lst = [
            [('event', self.event_cls, [self])],
            [('gui', self.gui_cls, [self, self.menu_args, carpage_props])]]
        GameObject.__init__(self, init_lst)
        PageFacade.__init__(self)


class CarPageSeason(CarPage):
    gui_cls = CarPageGuiSeason


class CarPageServer(CarPage):
    gui_cls = CarPageGuiServer


class CarPageClient(CarPage):
    gui_cls = CarPageGuiClient
