import time
import ccxt
from decimal import Decimal, ROUND_DOWN
from typing import Dict, List

class GateWithdraw:
    def __init__(self, credentials: Dict):
        """初始化Gate提币类"""
        self.exchange = ccxt.gateio({
            'apiKey': credentials['api_key'],
            'secret': credentials['api_secret'],
            'enableRateLimit': True
        })

        self.network_mapping = {
            'MATIC': 'polygon',    # Polygon/MATIC 网络
            'ERC20': 'eth',       # ETH/ERC20 网络
            'BEP20': 'bsc',         # BSC/BEP20 网络
            'OPBNB': 'opbnb',       # OPBNB 网络
            'ARBONE': 'arbevm',    # Arbitrum 网络
            'OPTIMISM': 'opeth',    # Optimism 网络
            'SOLANA': 'sol',      # Solana 网络
            'BASE': 'baseevm',    # BASE 网络
        }

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
                                'fee': network.get('withdrawFee', 0),
                                'min': network.get('withdrawMin', 0)
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
            
            # 获取币种信息
            currencies = self.exchange.fetch_currencies()
            if coin not in currencies:
                raise Exception(f'无法获取 {coin} 的币种信息')
            
            # 检查网络是否支持
            currency_info = currencies[coin]
            network_info = None
            for net_id, net in currency_info['networks'].items():
                if net_id == network:
                    network_info = net
                    break
            
            if not network_info:
                raise Exception(f'不支持的网络: {network}')

            # 检查最小提币量
            min_withdraw = float(network_info.get('withdrawMin', 0))
            withdrawal_fee = float(network_info.get('withdrawFee', 0))

            # 检查余额
            balance = self.exchange.fetch_balance()
            if coin not in balance:
                raise Exception(f'无法获取 {coin} 余额')
            
            available_balance = float(balance[coin]['free'])
            adjusted_amount = self._adjust_precision(float(amount))

            # 检查最小提币限额
            if adjusted_amount < min_withdraw:
                raise Exception(f'提币金额 {adjusted_amount} {coin} 小于最小提币限额 {min_withdraw} {coin}')
            
            # 检查余额是否充足（包含手续费）
            if adjusted_amount + withdrawal_fee > available_balance:
                raise Exception(f'余额不足，当前可用余额: {available_balance} {coin}，需要金额: {adjusted_amount + withdrawal_fee} {coin}')

            # 执行提币
            withdrawal = self.exchange.withdraw(
                code=coin,
                amount=adjusted_amount,
                address=address,
                tag=memo if memo else None,
                params={
                    'chain': network,
                    'withdraw_order_id': withdraw_order_id if withdraw_order_id else None,
                    'remark': remark if remark else None
                }
            )
            
            return {
                'code': 0,
                'msg': 'success',
                'data': {
                    'withdrawal': withdrawal
                }
            }

        except Exception as e:
            raise Exception(f"Gate提币失败: {str(e)}")

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