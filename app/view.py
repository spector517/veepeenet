from typing import Literal

from pydantic import BaseModel


class ClientView(BaseModel):
    name: str
    url: str

    def __repr__(self):
        return f'{self.name}: {self.url}'


class ServerView(BaseModel):
    veepeenet_version: str
    veepeenet_build: int
    xray_version: str
    server_status: Literal['Running', 'Stopped']
    server_host: str
    server_port: int
    reality_address: str
    reality_names: list[str]
    clients: list[ClientView]

    def __repr__(self):
        clients_repr = '\n'.join([f'\t\t{repr(client)}' for client in self.clients]) \
            if self.clients else '\t\tServer has no clients'
        return ('----------- '
        f'VeePeeNET {self.veepeenet_version} build {self.veepeenet_build}'
        ' -----------\n'
        'Xray server info:\n'
        f'\tversion: {self.xray_version}\n'
        f'\tstatus: {self.server_status}\n'
        f'\taddress: {self.server_host}:{self.server_port}\n'
        f'\treality_address: {self.reality_address}\n'
        f'\treality_names: {", ".join(self.reality_names)}\n'
        f'\tclients:\n'
        f'{clients_repr}\n'
        '---------------------------------------------------')

class VersionsView(BaseModel):
    veepeenet_version: str
    veepeenet_build: int
    xray_version: str
