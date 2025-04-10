import time
import ccxt
from typing import Dict, List
from decimal import Decimal, ROUND_DOWN

class BinanceWithdraw:
    def __init__(self, credentials: Dict):
        """初始化Binance提币类"""
        self.exchange = ccxt.binance({
            'apiKey': credentials['api_key'],
            'secret': credentials['api_secret'],
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot'
            }
        })

    def _adjust_precision(self, amount: float, precision: int = 5) -> float:
        """调整金额精度，统一使用5位小数"""
        decimal_amount = Decimal(str(amount))
        step = Decimal('0.' + '0' * (precision - 1) + '1')  # 0.00001 for precision=5
        adjusted = (decimal_amount / step).quantize(Decimal('1'), rounding=ROUND_DOWN) * step
        return float(adjusted)

    def get_coinlist(self) -> List[Dict]:
        """获取币种列表及其支持的网络"""
        try:
            currencies = self.exchange.fetch_currencies()
            
            coin_list = []
            for currency_id, currency in currencies.items():
                if 'networks' in currency and currency['networks']:
                    networks = []
                    for network_id, network in currency['networks'].items():
                        if network['withdraw']:  # 只添加可提现的网络
                            networks.append({
                                'network': network_id,
                                'fee': network.get('withdrawFee', 0)
                            })
                    if networks:  # 只添加有可用网络的币种
                        coin_list.append({
                            'coin': currency_id,
                            'networkList': networks
                        })
            
            return coin_list
        except Exception as e:
            raise Exception(f"获取币种列表失败: {str(e)}")

    async def withdraw(self, coin: str, network: str, address: str, 
                      amount: str, memo: str = '', 
                      withdraw_order_id: str = '', 
                      remark: str = '') -> Dict:
        """执行提币操作"""
        try:
            # 检查余额
            balance = self.exchange.fetch_balance()
            
            if coin not in balance:
                raise Exception(f'无法获取 {coin} 余额')
            
            available_balance = float(balance[coin]['free'])
            
            # 调整金额精度
            adjusted_amount = self._adjust_precision(float(amount))
            
            if adjusted_amount > available_balance:
                raise Exception(f'余额不足，当前可用余额: {available_balance} {coin}')

            if adjusted_amount <= 0:
                raise Exception(f'提币金额必须大于0: {adjusted_amount} {coin}')

            # 构建提币参数
            params = {
                'network': network
            }

            if memo:
                params['memo'] = memo

            if withdraw_order_id:
                params['withdrawOrderId'] = withdraw_order_id

            # 执行提币
            withdraw_response = self.exchange.withdraw(
                code=coin,
                amount=adjusted_amount,
                address=address,
                tag=memo if memo else None,
                params=params
            )

            # 等待5秒后查询状态
            time.sleep(5)
            
            # 获取最近的提现历史
            withdrawals = self.exchange.fetch_withdrawals(code=coin, limit=1)
            status = withdrawals[0] if withdrawals else None

            return {
                'code': 0,
                'msg': 'success',
                'data': {
                    'withdrawal': withdraw_response,
                    'status': status
                }
            }

        except Exception as e:
            raise Exception(f"Binance提币失败: {str(e)}")

    def get_available_coins(self) -> List[Dict]:
        """获取所有可用币种及其网络信息"""
        try:
            coin_list = self.get_coinlist()
            available_coins = []
            for coin_info in coin_list:
                if 'networkList' in coin_info and coin_info.get('networkList'):
                    available_coins.append({
                        'coin': coin_info['coin'],
                        'networks': [network['network'] for network in coin_info['networkList']]
                    })
            return available_coins
        except Exception as e:
            raise Exception(f"获取币种列表失败: {str(e)}")

    def get_coin_networks(self, coin: str) -> List[str]:
        """获取指定币种的可用网络"""
        try:
            coin_list = self.get_coinlist()
            for coin_info in coin_list:
                if coin_info['coin'].upper() == coin.upper():
                    if 'networkList' in coin_info:
                        return [network['network'] for network in coin_info['networkList']]
            return []
        except Exception as e:
            raise Exception(f"获取网络列表失败: {str(e)}")