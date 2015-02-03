#!/usr/bin/env python
# -*- coding: utf-8 -*-

import cherrypy
import htpc
import logging
import requests

from urllib import urlencode
from urllib2 import urlopen
from json import loads
from htpc.proxy import get_image


class Headphones(object):
    def __init__(self):
        self.logger = logging.getLogger('modules.headphones')
        htpc.MODULES.append({
            'name': 'Headphones',
            'id': 'headphones',
            'test': htpc.WEBDIR + 'headphones/ping',
            'fields': [
                {'type': 'bool', 'label': 'Enable', 'name': 'headphones_enable'},
                {'type': 'text', 'label': 'Menu name', 'name': 'headphones_name'},
                {'type': 'text', 'label': 'IP / Host *', 'name': 'headphones_host'},
                {'type': 'text', 'label': 'Port *', 'name': 'headphones_port'},
                {'type': 'text', 'label': 'Basepath', 'name': 'headphones_basepath'},
                {'type': 'text', 'label': 'API key', 'name': 'headphones_apikey'},
                {'type': 'bool', 'label': 'Use SSL', 'name': 'headphones_ssl'},
            ]
        })

    @cherrypy.expose()
    def index(self):
        template = htpc.LOOKUP.get_template('headphones.html')
        settings = htpc.settings
        url = self._build_url()

        return template.render(
            scriptname='headphones',
            hello='world',
            settings=settings,
            url=url,
            name=settings.get('headphones_name') or 'Headphones',
        )

    @cherrypy.expose()
    def GetThumb(self, url, thumb=None, h=None, w=None, o=100):
        """ Parse thumb to get the url and send to htpc.proxy.get_image """
        #url = url('/images/DefaultVideo.png')

        self.logger.debug("Trying to fetch image via %s", url)
        print url
        return get_image(url, h, w, o)


    @cherrypy.expose()
    def viewArtist(self, artist_id):
        response = self.fetch('getArtist&id=%s' % artist_id)

        for a in response['albums']:
            a['StatusText'] = _get_status_icon(a['Status'])
            a['can_download'] = True if a['Status'] not in ('Downloaded', 'Snatched', 'Wanted') else False

        template = htpc.LOOKUP.get_template('headphones_view_artist.html')
        return template.render(
            scriptname='headphones_view_artist',
            artist_id=artist_id,
            artist=response['artist'][0],
            artistimg=response['artist'][0]['ArtworkURL'],
            albums=response['albums'],
            description=response['description'][0],
            module_name=htpc.settings.get('headphones_name') or 'Headphones',
        )

    @cherrypy.expose()
    def viewAlbum(self, album_id):
        response = self.fetch('getAlbum&id=%s' % album_id)

        tracks = response['tracks']
        for t in tracks:
            duration = t['TrackDuration']
            total_seconds = duration / 1000
            minutes = total_seconds / 60
            seconds = total_seconds - (minutes * 60)
            t['DurationText'] = '%d:%02d' % (minutes, seconds)
            t['TrackStatus'] = _get_status_icon('Downloaded' if t['Location'] is not None else '')

        template = htpc.LOOKUP.get_template('headphones_view_album.html')
        return template.render(
            scriptname='headphones_view_album',
            artist_id=response['album'][0]['ArtistID'],
            album_id=album_id,
            c_img=response['album'][0]['ArtworkURL'],
            albumimg=response['album'][0]['ArtworkURL'],
            #artistimg=response['artist'][0]['ArtworkURL'],
            module_name=htpc.settings.get('headphones_name', 'Headphones'),
            album=response['album'][0],
            tracks=response['tracks'],
            description=response['description'][0]
        )

    @staticmethod
    def _build_url(ssl=None, host=None, port=None, base_path=None):
        ssl = ssl or htpc.settings.get('headphones_ssl')
        host = host or htpc.settings.get('headphones_host')
        port = port or htpc.settings.get('headphones_port')
        base_path = base_path or htpc.settings.get('headphones_basepath')

        path = base_path or '/'
        if path.startswith('/') is False:
            path = '/' + path
        if path.endswith('/') is False:
            path += '/'

        url = '{protocol}://{host}:{port}{path}'.format(
            protocol='https' if ssl else 'http',
            host=host,
            port=port,
            path=path,
        )

        return url

    @staticmethod
    def _build_api_url(command, url=None, api_key=None):
        return '{url}api?apikey={api_key}&cmd={command}'.format(
            url=url or Headphones._build_url(),
            api_key=api_key or htpc.settings.get('headphones_apikey'),
            command=command,
        )


    @cherrypy.expose()
    @cherrypy.tools.json_out()
    def GetArtistList(self):
        return self.fetch('getIndex')

    @cherrypy.expose()
    @cherrypy.tools.json_out()
    def GetWantedList(self):
        return self.fetch('getWanted')

    @cherrypy.expose()
    @cherrypy.tools.json_out()
    def SearchForArtist(self, name, searchtype):
        if searchtype == "artistId":
            return self.fetch('findArtist&%s' % urlencode({'name': name}))
        else:
            return self.fetch('findAlbum&%s' % urlencode({'name': name}))

        #return self.fetch('findArtist&%s' % urlencode({'name': name}))

    @cherrypy.expose()
    @cherrypy.tools.json_out()
    def RefreshArtist(self, artistId):
        return self.fetch('refreshArtist&id=%s' % artistId)

    @cherrypy.expose()
    @cherrypy.tools.json_out()
    def DeleteArtist(self, artistId):
        return self.fetch('delArtist&id=%s' % artistId)

    @cherrypy.expose()
    @cherrypy.tools.json_out()
    def QueueAlbum(self, albumId):
        return self.fetch('queueAlbum&id=%s' % albumId)

    @cherrypy.expose()
    @cherrypy.tools.json_out()
    def UnqueueAlbum(self, albumId):
        return self.fetch('unqueueAlbum&id=%s' % albumId)

    @cherrypy.expose()
    @cherrypy.tools.json_out()
    def AddArtist(self, id, searchtype, **kwargs):
        if searchtype == "artistId":
            return self.fetch('addArtist&id=%s' % id)
        else:
            return self.fetch('addAlbum&id=%s' % id)

    @cherrypy.expose()
    @cherrypy.tools.json_out()
    def GetHistoryList(self):
        return self.fetch('getHistory')

    @cherrypy.expose()
    def GetAlbumArt(self, id):
        return self.fetch('getAlbumArt&id=%s' % id, img=True)

    @cherrypy.expose()
    def artwork(self):
        return self.fetch("artwork/artist/9756f302-28a0-4d4f-b296-e6d7bf7d187d", img=True)

    def fetch(self, command, url=None, api_key=None, img=False):
        url = Headphones._build_api_url(command, url, api_key)

        try:
            self.logger.info('calling api @ %s' % url)
            response = requests.get(url, timeout=30) # change timeout as mb is fucking slow

            if response.status_code != 200:
                self.logger.error('failed to contact headphones')
                return

            if img:
                return response.content

            json_body = response.json()
            self.logger.debug('response body: %s' % json_body)

            return json_body
        except Exception as e:
            self.logger.error("Error calling api %s: %s" % (url, e))

    @cherrypy.tools.json_out()
    @cherrypy.expose()
    def ping(self,
             headphones_enable, headphones_name,
             headphones_host, headphones_port,
             headphones_basepath,
             headphones_apikey,
             headphones_ssl=False):

        url = self._build_url(
            headphones_ssl,
            headphones_host,
            headphones_port,
            headphones_basepath,
        )

        return self.fetch('getVersion', url, headphones_apikey)


def _get_status_icon(status):
    if not status:
        return ''

    if status == 'Downloaded':
        fmt = '<span class="label label-success"><i class="icon-download-alt icon-white"></i> %s</span>'
    else:
        fmt = '<span class="label">%s</span>'

    return fmt % status