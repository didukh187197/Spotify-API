import os

import requests
import json
from dependencies import logger
import csv

import yaml
import base64

_REFRESH_TOKEN_PATH = 'refresh_token.txt'
_BASE_64_ENCODING = 'ascii'

_GRANT_TYPE_AUTH_CODE = 'authorization_code'
_GRANT_TYPE_REFRESH_TOKEN = 'refresh_token'

log = logger.setup_logger(__name__)


def _get_token_endpoint_response(grant_type):
    config = _get_configuration()

    client_id = config['clientId']
    client_secret = config['clientSecret']
    authorization_code = config['authorizationCode']
    redirect_url = config['redirectUrl']

    token_endpoint = config['tokenEndpoint']

    message_bytes = f"{client_id}:{client_secret}".encode(_BASE_64_ENCODING)
    base64_bytes = base64.b64encode(message_bytes)
    base64_string = base64_bytes.decode(_BASE_64_ENCODING)

    headers = {'Authorization': f"Basic {base64_string}"}
    data = {'redirect_uri': redirect_url, 'grant_type': grant_type}

    if grant_type == _GRANT_TYPE_AUTH_CODE:
        data['code'] = authorization_code
    elif grant_type == _GRANT_TYPE_REFRESH_TOKEN and os.path.isfile(_REFRESH_TOKEN_PATH):
        refresh_token = open(_REFRESH_TOKEN_PATH, "r").read()
        data['refresh_token'] = refresh_token
    else:
        print('Unknown grant type - unable to generate access token.')
        exit(-1)

    response = requests.post(token_endpoint, data=data, headers=headers)
    return response


def _retrieve_access_token():
    auth_code_type_response = _get_token_endpoint_response(_GRANT_TYPE_AUTH_CODE)
    if auth_code_type_response.status_code == 200:
        log.debug('Trying to retrieve access token using AUTHORIZATION CODE.')
        auth_code_type_response = json.loads(auth_code_type_response.content)
        access_token = auth_code_type_response['access_token']
        refresh_token = auth_code_type_response['refresh_token']

        f = open(_REFRESH_TOKEN_PATH, "x")
        f.write(refresh_token)
        f.close()
    else:
        log.debug('Trying to retrieve access token using REFRESH TOKEN.')
        refresh_token_type_response = _get_token_endpoint_response(_GRANT_TYPE_REFRESH_TOKEN)
        refresh_token_type_response = json.loads(refresh_token_type_response.content)
        access_token = refresh_token_type_response['access_token']
    return access_token


def _get_configuration():
    with open('config.yml') as f:
        return yaml.safe_load(f)


def _retrieve_from_get_endpoint(url, token):
    headers = {"Authorization": f"Bearer {token}"}

    log.debug(f"Trying to access: '{url}'")
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        log.error(f"Unable to continue execution due to '{response.status_code}' code.")
        log.error(response.content)
        exit(0)
    log.debug(f"The response is successfully retrieved from: '{url}'")

    return response


def _prepare_user_tracks(access_token):
    # TODO: handle different types of tokens.
    user_tracks_resp = _retrieve_from_get_endpoint('https://api.spotify.com/v1/me/tracks?limit=50',
                                                   access_token)
    user_tracks_obj = json.loads(user_tracks_resp.content)['items']
    user_tracks_list = []
    for i in user_tracks_obj:
        user_tracks_dict = {
            'name': i['track']['name'],
            'artist': [a['name'] for a in i['track']['artists']],
            'duration_ms': i['track']['duration_ms'],
            'added_at': i['added_at']
        }
        user_tracks_list.append(user_tracks_dict)

    my_tracks_basic_info_file_name = 'my_tracks_basic_info.csv'
    with open(my_tracks_basic_info_file_name, 'w', ) as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['name', 'artist', 'duration_ms', 'added_at'])
        for i in user_tracks_list:
            writer.writerow([i['name'], i['artist'], i['duration_ms'], i['added_at']])

        log.info(f"User's liked tracks have been saved to {my_tracks_basic_info_file_name}.")


def _prepare_playlist_tracks(playlist_name, access_token):
    log.info(f"Trying to fetch tracks from '{playlist_name}' playlist.")

    playlists_resp = _retrieve_from_get_endpoint('https://api.spotify.com/v1/me/playlists', access_token)
    playlists_obj = json.loads(playlists_resp.content)

    selected_playlist = playlists_obj['items'][0]
    for i in playlists_obj['items']:
        if i['name'] == playlist_name:
            selected_playlist = i

    playlist_items_resp = _retrieve_from_get_endpoint(
        f'https://api.spotify.com/v1/playlists/{selected_playlist["id"]}/tracks',
        access_token)
    playlist_items_obj = json.loads(playlist_items_resp.content)
    playlist_items_obj = playlist_items_obj['items']

    full_track_info_objs = []
    for i in playlist_items_obj:
        track_audio_features_resp = _retrieve_from_get_endpoint(
            f'https://api.spotify.com/v1/audio-features/{i["track"]["id"]}',
            access_token)
        track_audio_features_obj = json.loads(track_audio_features_resp.content)

        full_track_info = {"id": i["track"]["id"],
                           "name": i["track"]["name"],
                           "artist": [a["name"] for a in i["track"]["artists"]],
                           "popularity": i["track"]["popularity"],
                           "explicit": i["track"]["explicit"],
                           "danceability": track_audio_features_obj["danceability"],
                           "energy": track_audio_features_obj["energy"],
                           "key": track_audio_features_obj["key"],
                           "loudness": track_audio_features_obj["loudness"],
                           "mode": track_audio_features_obj["mode"],
                           "speechiness": track_audio_features_obj["speechiness"],
                           "acousticness": track_audio_features_obj["acousticness"],
                           "instrumentalness": track_audio_features_obj["instrumentalness"],
                           "liveness": track_audio_features_obj["liveness"],
                           "valence": track_audio_features_obj["valence"],
                           "tempo": track_audio_features_obj["tempo"],
                           "type": track_audio_features_obj["type"],
                           "time_signature": track_audio_features_obj["time_signature"],
                           "duration_ms": track_audio_features_obj["duration_ms"],
                           }
        full_track_info_objs.append(full_track_info)

    playlist_tracks_info_file_name = 'playlist_tracks_info.csv'
    with open(playlist_tracks_info_file_name, 'w', ) as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['id', 'name', 'artist', 'popularity', 'explicit', 'danceability',
                         'energy', 'key', 'loudness', 'mode', 'speechiness', 'acousticness',
                         'instrumentalness', 'liveness', 'valence', 'tempo', 'type',
                         'time_signature', 'duration_ms'])
        for i in full_track_info_objs:
            writer.writerow([i['id'], i['name'], i['artist'], i['popularity'],
                             i['explicit'], i['danceability'], i['energy'], i['key'],
                             i['loudness'], i['mode'], i['speechiness'], i['acousticness'],
                             i['instrumentalness'], i['liveness'], i['valence'], i['tempo'],
                             i['type'], i['time_signature'], i['duration_ms']])
        log.info(f"Tracks from '{playlist_name}' playlist successfully saved /"
                 f" to {playlist_tracks_info_file_name}.")


if __name__ == '__main__':
    access_token = _retrieve_access_token()
    _prepare_playlist_tracks('Świat Top 50', access_token)
