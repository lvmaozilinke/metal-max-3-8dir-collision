# -*- coding: utf-8 -*-
"""Metal Max 3 (NDS) 八方向/逐轴碰撞修复 -- 补丁数据

由 V166 镜像与原始 ARM9 镜像逐字节比较生成。
每一项 = (镜像内偏移, 原始字节, 修复后字节)。
偏移是“解码后的 ARM9 镜像”内的偏移(镜像基址 0x02000000)。
"""

import base64

# 解码后镜像的长度(所有可支持的 MM3 ROM 都应是这个长度)
IMAGE_SIZE = 0x117FD8

PATCHES = [
    (0xABE2,
     base64.b64decode(
         'OLUFHP/31/8EHATRCCA4vAi8BLAYRyWABaoSiAWpAyCBQwgdACEAKgjdAB0DHx1oiwDjGEkcXWCRQvbbASEgHAkC+Pe67wog'
         'IRwAIvv3D/oFHAZIIRwBIvj35f0IIAAtANsCIDi8CLwEsBhHwEbEZhECcLUGHA0c//ed/wQcAdEIIHC9MBwhHCoc7vf47iAc'
         'KRz495LvCiAhHAAi+/fn+QUcBEghHAEi+Pe9/QggAC0A2wIgcL3EZhECAUhAaHBHwEasZhECA0gAiAAoAdAAIHBHAyBwR6xm'
         'EQIQtf/38/8AKA3RB0wCIWBoQGj491jvYGhAaACIASgB2AMgEL0AIBC9rGYRAg+0OLX/99z/ACga0Q9MAiFgaEBo+PdA72Bo'
         'BKtAaAMik0MBiAScAyAdHQAsCdAAIy0dKh8SaIpCANEYHGQeBJT20Ti8CLwEsBhHwEasZhEC+LWGsJ9IDRxEaAAqANA34QEh'
         'IGkJAvj3GO/gigAoBNEBIWBoyQL49xDvIGmFQgTQASEoHAkC+PcI7yiILCg004AoDNFoiBMoAdH59w=='
     ),
     base64.b64decode(
         'YEtgShKIGmBaTCRoJIgwICBAANGk4MAgIEAA0aDgAiFAICBAANEAIVpLGWBcS+pvGmBZS2pvGmBXSxtoASso0AEhICAgQADR'
         'AyEA8Ij5KRzYMQiICCMYQExLGGApHNQxCIhKSxhgAiFAICBAANEAIQDwdfkpHNgxCIgII5hDQksaaBBDCIBBSxpoKRzUMQqA'
         'J+ACIUAgIEAA0QAhAPBf+Skc2DEIiAgjGEA3SxhgKRzUMQiINksYYAEhICAgQADRAyEA8Ez5KRzYMQiICCOYQy5LGmgQQwiA'
         'LUsaaCkc1DEKgC5LGGjqbxIaACoD0SlLASEZYAjgKEsYaGpvEhoAKgLQJEsAIRlgIksZaCgcxDABYCgcyDABYBpIAGgaSxmI'
         'iEIb0AoaEgYSDgIqFtEBOQkGCQ4ZgAEGCQ6KAAkBiRgEM1sYKRzEMQiIGIApRnQxCGhYYEhomGCIaNhgB0sYRwa0C0sAIclD'
         'GWAGvCgcA2hwR1QqDAJYKgwC9yoMAkAdAACQrQAChJwaApStAAKYrQACnK0AAqCtAAKkrQACqK0AAg=='
     )),
    (0xAE00,
     base64.b64decode('CYj4977uKYgEKQHQAikC0WiIACgG0AMpAdAAKQTRaIgAKAHQAPAe+SmIAikN0WiIACgK0YgAIBiEaf/3gf4ALA/QKBygRwaw'),
     base64.b64decode('DLQDHA5KEmgRDgIpEtESiDAgEEIO0MAgEEIL0AlK6AcE1QEtANFSQmJiA+AALQDQUkLiYhgcDLwhHCQxcEcAAFQqDAJQCwAA')),
    (0xAF00,
     base64.b64decode(
         'CIAAIkqAjoCKYMpgCoIFmsowSoIPhCFYKkgGIkGEKklBgwSZgYcDmChJ7vea7QKYACgE0CZJGCLu9zzsBOAkSQAgGCLu9yrs'
         'AC8B0QGZAOAAmSBIAC8BgAHQAZgAkB1JAJgYT0iAACawACEYCBz+gMwwAGgAKAfQQyCAAAhYzDH4YQloOByIR3AcAAQGDBAu'
         '6tMBJjYCIGkxHPj38u0A8Bv4IGmFQgfQKYjwAQhDKIAoHDEc+Pfy7Qaw+L2sZhEC9f8AAAxnEQL//wAAIGcRAjBnEQJMZxEC'
         'BEoBIBGICEI='
     ),
     base64.b64decode(
         'YRgDSABoAAQADAJKEEcAAHDKGQKnJgwCB0sbaFsGCNQGShCIIUaUMQiADDoQiAw5CIAKsBC9AACsyhkChMoZAgi1CxwoHMgw'
         'A2AoHARKEmi38Jr6KGgDSUAYACEBYAi9WCoMAkAdAACwACEYCBz+gMwwAGgAKAfQQyCAAAhYzDERS+MaACsH0BBL4xoAKwPQ'
         'D0vjGgArEtEQSxtoWwYO1AxIAIhAB0APgAALSxuIJRyQNSuAJRyINf8jK4AB4EAPkUNwRwAAAAAwyxkCcMwZArDNGQKEyhkC'
         'gMoZAqzKGQI='
     )),
    (0x2CC72,
     base64.b64decode('QA+RQw=='),
     base64.b64decode('3veF+Q==')),
    (0x38A76,
     base64.b64decode('IRwkMQ=='),
     base64.b64decode('0vfD+Q==')),
    (0xC26A2,
     base64.b64decode('B5hhGA=='),
     base64.b64decode('SPct/A==')),
    (0xC277C,
     base64.b64decode('KBwDaA=='),
     base64.b64decode('SPcx+g==')),
    (0xC2948,
     base64.b64decode('KVI='),
     base64.b64decode('wEY=')),
    (0xC2E56,
     base64.b64decode('CrAQvQ=='),
     base64.b64decode('SPdf+A==')),
]
