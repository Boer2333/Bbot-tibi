import time
import ccxt
from decimal import Decimal, ROUND_DOWN
from typing import Dict, List

class BitgetWithdraw:
    def __init__(self, credentials: Dict):
        """初始化Bitget提币类"""
        self.exchange = ccxt.bitget({
            'apiKey': credentials['api_key'],
            'secret': credentials['api_secret'],
            'password': credentials['password'],  # Bitget需要密码
            'enableRateLimit': True
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

            # 执行提币
            # ccxt withdraw 方法的标准格式：withdraw(code, amount, address, tag=None, params={})
            withdrawal = self.exchange.withdraw(
                code=coin,           # 币种代码
                amount=adjusted_amount,  # 数量
                address=address,     # 地址
                tag=memo if memo else None,  # memo/tag
                params={'network': network}  # 额外参数，包括网络选择
            )
            
            return {
                'code': 0,
                'msg': 'success',
                'data': {
                    'withdrawal': withdrawal
                }
            }

        except Exception as e:
            raise Exception(f"Bitget提币失败: {str(e)}")

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