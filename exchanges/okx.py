import time
import ccxt
from typing import Dict, List
from decimal import Decimal, ROUND_DOWN

class OkxWithdraw:
    def __init__(self, credentials: Dict):
        """初始化OKX提币类"""
        self.exchange = ccxt.okx({
            'apiKey': credentials['api_key'],
            'secret': credentials['api_secret'],
            'password': credentials['password'],  # OKX需要密码
            'enableRateLimit': True
        })
    def _adjust_precision(self, amount: float, precision: int = 5) -> float:
        """调整金额精度，OKX通常最多支持5位小数"""
        decimal_amount = Decimal(str(amount))
        step = Decimal('0.' + '0' * (precision - 1) + '1')  # 0.00001 for precision=5
        adjusted = (decimal_amount / step).quantize(Decimal('1'), rounding=ROUND_DOWN) * step
        return float(adjusted)

    def get_coinlist(self) -> List[Dict]:
        """获取币种列表及其支持的网络"""
        try:
            currencies = self.exchange.fetchCurrencies()
            coin_list = []
            
            for currency, data in currencies.items():
                if 'networks' in data and data['networks']:
                    networks = []
                    for network in data['networks'].values():
                        if 'info' in network and 'chain' in network['info']:
                            networks.append({
                                'network': network['info']['chain'],
                                'fee': network['fee']
                            })
                    if networks:
                        coin_list.append({
                            'coin': currency,
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
            # 获取提币费用
            currencies = self.exchange.fetchCurrencies()
            withdrawal_fee = None
            for key, value in currencies[coin]['networks'].items():
                if 'info' in value and value['info']['chain'] == network:
                    withdrawal_fee = value['fee']
                    break
            
            if not withdrawal_fee:
                raise Exception(f'无法获取 {network} 网络的提币费用信息')

            # 检查余额
            balance = self.exchange.privateGetAssetBalances()['data']
            available_balance = None
            for bal in balance:
                if bal['ccy'] == coin:
                    available_balance = float(bal['availBal'])
                    break

            if available_balance is None:
                raise Exception(f'无法获取 {coin} 余额')

            if available_balance < (float(amount) + withdrawal_fee):
                raise Exception(f'余额不足，当前可用余额: {available_balance} {coin}')
            
            adjusted_amount = self._adjust_precision(float(amount))
            # 构建提币参数
            params = {
                'ccy': coin,
                'amt': str(adjusted_amount),
                'dest': 4,  # 4表示外部地址
                'toAddr': address,
                'fee': withdrawal_fee,
                'chain': network
            }

            # 如果有memo，添加到地址中
            if memo:
                params['toAddr'] = f'{address}:{memo}'

            # 执行提币
            withdrawal = self.exchange.privatePostAssetWithdrawal(params)
            
            # 等待5秒获取状态
            time.sleep(5)
            status = self.exchange.privateGetAssetDepositWithdrawStatus(
                params={'wdId': withdrawal['data'][0]['wdId']}
            )

            # 返回结果
            return {
                'code': 0,
                'msg': 'success',
                'data': {
                    'withdrawal': withdrawal['data'],
                    'status': status['data']
                }
            }

        except Exception as e:
            raise Exception(f"OKX提币失败: {str(e)}")

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