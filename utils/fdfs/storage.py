from django.core.files.storage import Storage
from fdfs_client.client import Fdfs_client
from dailyfresh import settings
class FDFSStorage(Storage):
    def __init__(self, client_conf=None, base_url=None):
        '''初始化'''
        if client_conf is None:
            client_conf = settings.FDFS_CLIENT_CONF
        self.client_conf = client_conf

        if base_url is None:
            base_url = settings.FDFS_URL
        self.base_url = base_url

    def _open(self,name,mode='rb'):
        pass

    def _save(self,name,content):
        client = Fdfs_client(self.client_conf)
        res = client.upload_by_buffer(content.read())
        if res.get('Status') != 'Upload successed.':
            raise Exception('上传文件到fast dfs失败')
        filename = res.get('Remote file_id')
        return filename

    def exists(self, name):
        return False

    def url(self, name):
        return self.base_url+name