import httplib2

from apiclient.discovery import build
from oauth2client.client import OAuth2WebServerFlow, AccessTokenCredentials
from oauth2client.client import flow_from_clientsecrets

from flask import Flask, render_template, request, session, url_for, redirect

def get_oauth_flow():
    # client_secrets.json should look like this:
    # {
    #   "web": {
    #     "client_id": "...",
    #     "client_secret": "...",
    #     "redirect_uris": [],
    #     "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    #     "token_uri": "https://accounts.google.com/o/oauth2/token"
    #   }
    # }
    CLIENTSECRETS_LOCATION = 'client_secrets.json'
    REDIRECT_URI = url_for('oauth_callback', _external=True, _scheme='http')

    SCOPES = [
        'https://www.googleapis.com/auth/youtube.readonly'
    ]

    flow = flow_from_clientsecrets(CLIENTSECRETS_LOCATION, ' '.join(SCOPES))
    flow.redirect_uri = REDIRECT_URI

    return flow

def build_youtube(credentials):
    return build('youtube', 'v3', http=credentials.authorize(httplib2.Http()))


app = Flask(__name__)

@app.route('/')
def index():
    if 'access_token' in session:
        credentials = AccessTokenCredentials(session['access_token'], '')

        youtube = build_youtube(credentials)

        return render_template('callback.html',
                               playlists=get_playlists(youtube))

    flow = get_oauth_flow()

    authorize_url = flow.step1_get_authorize_url()

    return '<a href="%s">login</a>' % authorize_url

def get_playlists(youtube):
    channels_response = youtube.playlists().list(
        mine=True,
        part="snippet",
        maxResults=30
    ).execute()

    playlists = []

    for playlist in channels_response["items"]:
        playlist_data = {
            'title':  playlist['snippet']['title'],
            'id': playlist['id'],
            'videos': []
        }

        playlistitems_list_request = youtube.playlistItems().list(
            playlistId=playlist_data['id'],
            part="snippet,id",
            maxResults=50
        )

        while playlistitems_list_request:
            playlistitems_list_response = playlistitems_list_request.execute()

            for playlist_item in playlistitems_list_response["items"]:
                playlist_data['videos'].append({
                    'title': playlist_item["snippet"]["title"],
                    'ts': playlist_item['snippet']['publishedAt'],
                    'id': playlist_item["snippet"]["resourceId"]["videoId"]
                })

            playlistitems_list_request = youtube.playlistItems().list_next(
                playlistitems_list_request, playlistitems_list_response)

        playlists.append(playlist_data)

    return playlists

@app.route('/oauth2callback')
def oauth_callback():
    flow = get_oauth_flow()

    code = request.args.get('code', '')

    credentials = flow.step2_exchange(code)

    session['access_token'] = credentials.access_token

    return redirect('/')


if __name__ == '__main__':
    import os
    app.secret_key = os.urandom(24)
    app.run(debug=True)
