'''Module for IQ Option websocket.'''

import json
import logging
import websocket

from threading import Thread

import hermes.constants as constants


class WebsocketClient(object):
    '''Class for work with IQ Option websocket.'''

    def __init__(self, api):
        '''
        :param api: The instance of :class:`Hermes <hermes.api.Hermes>`.
        '''
        self.api = api
        self.wss = websocket.WebSocketApp(
            self.api.wss_url,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open)

    def dict_queue_add(self, dict, maxdict, key1, key2, key3, value):
        if key3 in dict[key1][key2]:
            dict[key1][key2][key3] = value
        else:
            while True:
                try:
                    dic_size = len(dict[key1][key2])
                except:
                    dic_size = 0
                if dic_size < maxdict:
                    dict[key1][key2][key3] = value
                    break
                else:
                    # del mini key
                    del dict[key1][key2][sorted(
                        dict[key1][key2].keys(), reverse=False)[0]]

    def api_dict_clean(self, obj):
        if len(obj) > 5000:
            for k in obj.keys():
                del obj[k]
                break

    def on_message(self, message):
        '''Method to process websocket messages.'''
        self.api.ssl_mutual_exclusion = True

        logger = logging.getLogger(__name__)
        logger.debug(message)

        message = json.loads(str(message))

        if message['name'] == 'timeSync':
            self.api.time_sync.server_timestamp = message['msg']
        elif message['name'] == 'candle-generated':
            Active_name = list(constants.ACTIVES.keys())[list(
                constants.ACTIVES.values()).index(message['msg']['active_id'])]

            active = str(Active_name)
            size = int(message['msg']['size'])
            from_ = int(message['msg']['from'])
            msg = message['msg']
            maxdict = self.api.real_time_candles_max_dict_table[Active_name][size]

            self.dict_queue_add(self.api.real_time_candles,
                                maxdict, active, size, from_, msg)
            self.api.candle_generated_check[active][size] = True

        elif message['name'] == 'options':
            self.api.get_options_v2_data = message
        elif message['name'] == 'candles-generated':
            Active_name = list(constants.ACTIVES.keys())[list(
                constants.ACTIVES.values()).index(message['msg']['active_id'])]
            active = str(Active_name)
            for k, v in message['msg']['candles'].items():
                v['active_id'] = message['msg']['active_id']
                v['at'] = message['msg']['at']
                v['ask'] = message['msg']['ask']
                v['bid'] = message['msg']['bid']
                v['close'] = message['msg']['value']
                v['size'] = int(k)
                size = int(v['size'])
                from_ = int(v['from'])
                maxdict = self.api.real_time_candles_max_dict_table[Active_name][size]
                msg = v
                self.dict_queue_add(self.api.real_time_candles,
                                    maxdict, active, size, from_, msg)

            self.api.candle_generated_all_size_check[active] = True
        elif message['name'] == 'commission-changed':
            instrument_type = message['msg']['instrument_type']
            active_id = message['msg']['active_id']
            Active_name = list(constants.ACTIVES.keys())[list(
                constants.ACTIVES.values()).index(active_id)]
            commission = message['msg']['commission']['value']
            self.api.subscribe_commission_changed_data[instrument_type][Active_name][self.api.time_sync.server_timestamp] = int(
                commission)
        elif message['name'] == 'heartbeat':
            try:
                self.api.heartbeat(message['msg'])
            except:
                pass
        elif message['name'] == 'balances':
            self.api.balances_raw = message
        elif message['name'] == 'profile':
            self.api.profile.msg = message['msg']

            if self.api.profile.msg != False:
                try:
                    self.api.profile.balance = message['msg']['balance']
                except:
                    pass
                if self.api.balance_id == None:
                    for balance in message['msg']['balances']:
                        if balance['type'] == 4:
                            self.api.balance_id = balance['id']
                            break
                try:
                    self.api.profile.balance_id = message['msg']['balance_id']
                except:
                    pass

                try:
                    self.api.profile.balance_type = message['msg']['balance_type']
                except:
                    pass

                try:
                    self.api.profile.balances = message['msg']['balances']
                except:
                    pass
        elif message['name'] == 'balance-changed':
            balance = message['msg']['current_balance']

            try:
                self.api.profile.balance = balance['amount']
            except:
                pass

            try:
                self.api.profile.balance_id = balance['id']
            except:
                pass

            try:
                self.api.profile.balance_type = balance['type']
            except:
                pass
        elif message['name'] == 'candles':
            try:
                self.api.candles.candles_data = message['msg']['candles']
            except:
                pass
        elif message['name'] == 'buyComplete':
            try:
                self.api.buy_successful = message['msg']['isSuccessful']
                self.api.buy_id = message['msg']['result']['id']
            except:
                pass
        elif message['name'] == 'option':
            self.api.buy_multi_option[str(
                message['request_id'])] = message['msg']
        elif message['name'] == 'listInfoData':
            for get_m in message['msg']:
                self.api.list_info_data.set(
                    get_m['win'], get_m['game_state'], get_m['id'])
        elif message['name'] == 'socket-option-opened':
            id = message['msg']['id']
            self.api.socket_option_opened[id] = message
        elif message['name'] == 'api_option_init_all_result':
            self.api.api_option_init_all_result = message['msg']
        elif message['name'] == 'initialization-data':
            self.api.api_option_init_all_result_v2 = message['msg']
        elif message['name'] == 'underlying-list':
            self.api.underlying_list_data = message['msg']
        elif message['name'] == 'instruments':
            self.api.instruments = message['msg']
        elif message['name'] == 'financial-information':
            self.api.financial_information = message
        elif message['name'] == 'position-changed':
            self.api.position_changed = message

            if message['microserviceName'] == 'portfolio' and (message['msg']['source'] == 'digital-options') or message['msg']['source'] == 'trading':
                order_id = int(message['msg']['raw_event']['order_ids'][0])

                self.api.order_async[order_id][message['name']] = message

                if message['msg']['status'] == 'closed':
                    self.api.closed_options[order_id] = message['msg']

                    result = 'win'

                    if message['msg']['pnl'] < 0:
                        result = 'loose'

                    self.api.closed_options[order_id]['result'] = result
            elif message['microserviceName'] == 'portfolio' and message['msg']['source'] == 'binary-options':
                order_id = int(message['msg']['external_id'])

                self.api.order_async[order_id][message['name']] = message

                if message['msg']['status'] == 'open':
                    payload = message['msg']
                    payload.update({
                        'order_id': order_id
                    })

                    self.api.opened_options[order_id] = payload
        elif message['name'] == 'order-changed':
            order_id = int(message['msg']['raw_event']['id'])

            payload = message['msg']
            payload.update({
                'order_id': order_id
            })

            self.api.opened_options[order_id] = payload
        elif message['name'] == 'option-opened':
            self.api.order_async[int(
                message['msg']['option_id'])][message['name']] = message
        elif message['name'] == 'option-closed':
            option_id = int(message['msg']['option_id'])

            self.api.order_async[option_id][message['name']] = message
            self.api.closed_options[option_id] = message['msg']

            if message['microserviceName'] == 'binary-options':
                self.api.order_binary[message['msg']
                                      ['option_id']] = message['msg']
        elif message['name'] == 'top-assets-updated':
            self.api.top_assets_updated_data[str(
                message['msg']['instrument_type'])] = message['msg']['data']
        elif message['name'] == 'strike-list':
            self.api.strike_list = message
        elif message['name'] == 'api_game_betinfo_result':
            try:
                self.api.game_betinfo.isSuccessful = message['msg']['isSuccessful']
                self.api.game_betinfo.dict = message['msg']
            except:
                pass
        elif message['name'] == 'traders-mood-changed':
            self.api.traders_mood[message['msg']
                                  ['asset_id']] = message['msg']['value']
        elif message['name'] == 'order-placed-temp':
            self.api.buy_order_id = message['msg']['id']
        elif message['name'] == 'order':
            self.api.order_data = message
        elif message['name'] == 'positions':
            self.api.positions = message
        elif message['name'] == 'position':
            self.api.position = message
        elif message['name'] == 'deferred-orders':
            self.api.deferred_orders = message
        elif message['name'] == 'technical-indicators':
            if message['msg'].get('indicators') != None:
                self.api_dict_clean(self.api.technical_indicators)
                self.api.technical_indicators[message['request_id']
                                              ] = message['msg']['indicators']
            else:
                self.api.technical_indicators[message['request_id']] = {
                    'code': 'no_technical_indicator_available',
                    'message': message['msg']['message']
                }
        elif message['name'] == 'position-history':
            self.api.position_history = message
        elif message['name'] == 'history-positions':
            self.api.position_history_v2 = message
        elif message['name'] == 'available-leverages':
            self.api.available_leverages = message
        elif message['name'] == 'order-canceled':
            self.api.order_canceled = message
        elif message['name'] == 'position-closed':
            self.api.close_position_data = message
            self.api.sold_digital_options_respond = message
        elif message['name'] == 'overnight-fee':
            self.api.overnight_fee = message
        elif message['name'] == 'api_game_getoptions_result':
            self.api.api_game_get_options_result = message
        elif message['name'] == 'sold-options':
            self.api.sold_options_respond = message
        elif message['name'] == 'tpsl-changed':
            self.api.tpsl_changed_respond = message
        elif message['name'] == 'auto-margin-call-changed':
            self.api.auto_margin_call_changed_respond = message
        elif message['name'] == 'digital-option-placed':
            if message['msg'].get('id') is not None:
                self.api_dict_clean(self.api.digital_option_placed_id)
                self.api.digital_option_placed_id[message['request_id']
                                                  ] = message['msg']['id']
            else:
                self.api.digital_option_placed_id[message['request_id']] = {
                    'code': 'error_place_digital_order',
                    'error': message['msg']['message']
                }
        elif message['name'] == 'result':
            self.api.result = message['msg']['success']
        elif message['name'] == 'instrument-quotes-generated':
            Active_name = list(constants.ACTIVES.keys())[list(
                constants.ACTIVES.values()).index(message['msg']['active'])]
            period = message['msg']['expiration']['period']
            ans = {}

            for data in message['msg']['quotes']:
                if data['price']['ask'] == None:
                    ProfitPercent = None

                else:
                    askPrice = (float)(data['price']['ask'])
                    ProfitPercent = ((100-askPrice)*100)/askPrice

                for symble in data['symbols']:
                    try:
                        ans[symble] = ProfitPercent
                    except:
                        pass

            self.api.instrument_quites_generated_timestamp[Active_name][
                period] = message['msg']['expiration']['timestamp']
            self.api.instrument_quites_generated_data[Active_name][period] = ans
            self.api.instrument_quotes_generated_raw_data[Active_name][period] = message
        elif message['name'] == 'training-balance-reset':
            self.api.training_balance_reset_request = message['msg']['isSuccessful']
        elif message['name'] == 'socket-option-closed':
            id = message['msg']['id']
            self.api.socket_option_closed[id] = message
        elif message['name'] == 'live-deal-binary-option-placed':
            name = message['name']
            active_id = message['msg']['active_id']
            active = list(constants.ACTIVES.keys())[
                list(constants.ACTIVES.values()).index(active_id)]
            _type = message['msg']['option_type']

            try:
                self.api.live_deal_data[name][active][_type].appendleft(
                    message['msg'])
                if hasattr(self.api.binary_live_deal_cb, '__call__'):
                    cb_data = {
                        'active': active,
                        **message['msg']
                    }
                    realbinary = Thread(target=self.api.binary_live_deal_cb,
                                        kwargs=(cb_data))
                    realbinary.daemon = True
                    realbinary.start()
            except:
                pass
        elif message['name'] == 'live-deal-digital-option':
            name = message['name']
            active_id = message['msg']['instrument_active_id']
            active = list(constants.ACTIVES.keys())[
                list(constants.ACTIVES.values()).index(active_id)]
            _type = message['msg']['expiration_type']

            try:
                self.api.live_deal_data[name][active][_type].appendleft(
                    message['msg'])
                if hasattr(self.api.digital_live_deal_cb, '__call__'):
                    cb_data = {
                        'active': active,
                        **message['msg']
                    }
                    realdigital = Thread(target=self.api.digital_live_deal_cb,
                                         kwargs=(cb_data))
                    realdigital.daemon = True
                    realdigital.start()
            except:
                pass
        elif message['name'] == 'leaderboard-deals-client':
            self.api.leaderboard_deals_client = message['msg']
        elif message['name'] == 'live-deal':
            name = message['name']
            active_id = message['msg']['instrument_active_id']
            active = list(constants.ACTIVES.keys())[
                list(constants.ACTIVES.values()).index(active_id)]
            _type = message['msg']['instrument_type']

            try:
                self.api.live_deal_data[name][active][_type].appendleft(
                    message['msg'])
            except:
                pass
        elif message['name'] == 'user-profile-client':
            self.api.user_profile_client = message['msg']
        elif message['name'] == 'leaderboard-userinfo-deals-client':
            self.api.leaderboard_userinfo_deals_client = message['msg']
        elif message['name'] == 'users-availability':
            self.api.users_availability = message['msg']
        else:
            pass

        self.api.ssl_mutual_exclusion = False

    def on_error(self):
        '''Method to process websocket errors.'''
        logger = logging.getLogger(__name__)
        logger.error(error)

        self.api.websocket_error_reason = str(error)
        self.api.check_websocket_if_error = True

    def on_open(self):
        '''Method to process websocket open.'''
        logger = logging.getLogger(__name__)
        logger.debug('Websocket client connected.')

        self.api.check_websocket_if_connect = 1

    def on_close(self):
        '''Method to process websocket close.'''
        logger = logging.getLogger(__name__)
        logger.debug('Websocket connection closed.')

        self.api.check_websocket_if_connect = 0
