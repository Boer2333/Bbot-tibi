import requests
import hmac
import hashlib
from urllib.parse import urlencode, quote
from typing import Dict
from decimal import Decimal, ROUND_DOWN

# ServerTime、Signature
class TOOL(object):
    def _get_server_time(self):
        return requests.request('get', 'https://api.mexc.com/api/v3/time').json()['serverTime']

    def _sign_v3(self, req_time, sign_params=None):
        if sign_params:
            sign_params = urlencode(sign_params, quote_via=quote)
            to_sign = "{}&timestamp={}".format(sign_params, req_time)
        else:
            to_sign = "timestamp={}".format(req_time)
        sign = hmac.new(self.mexc_secret.encode('utf-8'), to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
        return sign

    def public_request(self, method, url, params=None):
        url = '{}{}'.format(self.hosts, url)
        return requests.request(method, url, params=params)

    def sign_request(self, method, url, params=None):
        url = '{}{}'.format(self.hosts, url)
        req_time = self._get_server_time()
        if params:
            params['signature'] = self._sign_v3(req_time=req_time, sign_params=params)
        else:
            params = {}
            params['signature'] = self._sign_v3(req_time=req_time)
        params['timestamp'] = req_time
        headers = {
            'x-mexc-apikey': self.mexc_key,
            'Content-Type': 'application/json',
        }
        return requests.request(method, url, params=params, headers=headers)

# Wallet
class MexcWithdraw(TOOL):
    def __init__(self, credentials: Dict):
        self.api = '/api/v3/capital'
        self.hosts = 'https://api.mexc.com'
        self.mexc_key = credentials['api_key']
        self.mexc_secret = credentials['api_secret']
        
        # 验证API连接
        try:
            time = self._get_server_time()
            print(f"\nMEXC API连接成功! 服务器时间: {time}")
        except Exception as e:
            raise Exception(f"MEXC API连接失败: {str(e)}")
    def _adjust_precision(self, amount: float, precision: int = 5) -> float:
        """调整金额精度，MEXC通常最多支持5位小数"""
        decimal_amount = Decimal(str(amount))
        step = Decimal('0.' + '0' * (precision - 1) + '1')  # 0.00001 for precision=5
        adjusted = (decimal_amount / step).quantize(Decimal('1'), rounding=ROUND_DOWN) * step
        return float(adjusted)

    def get_coinlist(self):
        """获取币种信息"""
        method = 'GET'
        url = '{}{}'.format(self.api, '/config/getall')
        response = self.sign_request(method, url)
        return response.json()

    async def withdraw(self, coin: str, network: str, address: str, 
                      amount: str, memo: str = '', 
                      withdraw_order_id: str = '', 
                      remark: str = '') -> Dict:
        """执行提币操作"""
        try:
            adjusted_amount = self._adjust_precision(float(amount))

            params = {
                "coin": coin,
                "address": address,
                "amount": str(adjusted_amount),
                "network": network,
                "memo": memo,
                "withdrawOrderId": withdraw_order_id,
                "remark": remark,
            }

            # 执行提币
            method = 'POST'
            url = '{}{}'.format(self.api, '/withdraw/apply')
            response = self.sign_request(method, url, params=params)
            return response.json()
            
        except Exception as e:
            raise Exception(f"MEXC提币失败: {str(e)}")

    def get_withdraw_history(self, params=None):
        """获取提币历史"""
        method = 'GET'
        url = '{}{}'.format(self.api, '/withdraw/history')
        response = self.sign_request(method, url, params=params)
        return response.json()

    def cancel_withdraw(self, params):
        """取消提币"""
        method = 'DELETE'
        url = '{}{}'.format(self.api, '/withdraw')
        response = self.sign_request(method, url, params=params)
        return response.json()