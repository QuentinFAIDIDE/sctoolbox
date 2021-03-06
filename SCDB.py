################################################################################
#IMPORTS
import soundcloud
import sys
import operator
import re
import random
from math import sqrt
################################################################################

################################################################################
#REGISTERING APP
def register():
    client = soundcloud.Client(client_id='47b5a3d7a326382120d95d8c663b47f7')
    return client
################################################################################

################################################################################
def searchForUser(client, name):
    container = client.get('/users', q=name)
    return container[0]
################################################################################

################################################################################
def extractProfile(client, user, shortversion = False, custom_profile=None, tracklimit=200, playlisting=True):
    end_page = False
    failcount = 0
    if custom_profile != None:
        profile = custom_profile
        len_beg = len(profile)
    else:
        profile = {}
        len_beg = 0
    likes_href = ('users/' + str(user.id) + '/favorites' )
    comments_href = ('users/' + str(user.id) + '/comments' )
    playlists_href = ('users/' + str(user.id) + '/playlists' )
    repost_href = ('https://api-v2.soundcloud.com/profile/soundcloud:users:' + str(user.id) + '?limit=10')
    if playlisting == False:
        playlists_href = 'stop'
    reposted_done = False
    end_playlist = False
    print("Profiling " + user.username)

    while(not end_page):
        #querying all the data
        if likes_href != 'stop':
            while True:
                try:
                    likes = client.get( likes_href , limit=50, linked_partitioning=1 )
                except:
                    print "Unexpected error:", sys.exc_info()[0]
                    continue
                break
            if hasattr(likes, 'next_href'):
                likes_href = likes.next_href
            else:
                likes_href = 'stop'

        if comments_href != 'stop':
            while True:
                try:
                    comments = client.get( comments_href , limit=50, linked_partitioning=1 )
                except:
                    print "Unexpected error:", sys.exc_info()[0]
                    continue
                break
            if hasattr(comments, 'next_href'):
                comments_href = comments.next_href
            else:
                comments_href = 'stop'

        if playlists_href != 'stop':
            while True:
                try:
                    playlists = client.get(playlists_href , limit=50, linked_partitioning=1 )
                    failcount = 0
                    if hasattr(playlists, 'next_href'):
                        playlists_href = playlists.next_href
                    else:
                        playlists_href = 'stop'
                except:
                    failcount += 1
                    if failcount >5:
                        end_playlist = True
                        playlists_href = 'stop'
                        break
                    continue
                break


        if not reposted_done:
            while True:
                try:
                    reposts = client.get((
                                'https://api-v2.soundcloud.com/profile/soundcloud:users:'
                                + str(user.id) + '?limit=10'))
                except:
                    print "Unexpected error:", sys.exc_info()[0]
                    continue
                break
                if hasattr(reposts, 'next_href'):
                    repost_href = reposts.next_href
                else:
                    repost_href = 'stop'
                    resposted_done = True

        if(reposted_done and likes_href == 'stop' and playlists_href == 'stop' and comments_href == 'stop'):
            end_page = True



        #processing playlists to extract tracks who are not from user
        if playlists_href != 'stop' :
            for playlist in playlists.collection:
                for track in playlist.tracks:
                    if track['user_id'] != user.id:
                        if user.username.lower() not in track['title'].lower():
                            if profile.has_key(str(track['id'])):
                                profile[str(track['id'])] += 2.0
                            else:
                                profile[str(track['id'])] = 2.0

        #processing all reposts to extract tracks who are not from user
        if (not reposted_done):
            for tracks in reposts.collection:
                if hasattr(tracks, 'track'):
                    if user.username.lower() not in tracks.track['title'].lower():
                        if profile.has_key(str(tracks.track['id'])):
                            profile[str(tracks.track['id'])] += 2.0
                        else:
                            profile[str(tracks.track['id'])] = 2.0
            reposted_done = True

        #processing all comments to get the tracks user commented
        #checking as always if they are not from him
        if comments_href != 'stop':
            for comment in comments.collection:
                if profile.has_key(str(comment.track_id)):
                    profile[str(comment.track_id)] += 2.0
                else:
                    profile[str(comment.track_id)] = 2.0

        #processing all likes to extract tracks who are not from user
        if likes_href != 'stop':
                for tracks in likes.collection:
                    if user.username.lower() not in tracks.title.lower():
                        if profile.has_key(str(tracks.id)):
                            profile[str(tracks.id)] += 1.0
                        else:
                            profile[str(tracks.id)] = 1.0
        if (len(profile))>tracklimit and shortversion==True: end_page = True

    #returning taste profile
    return profile
################################################################################

################################################################################
#PEARSON CORRELATION SCORE
#compare correlation between p1 and p2 critics and ignore grade inflation
def comparePearson(p1, p2):
    si={}
    for item in p1:
        if item in p2: si[item]=1

    n=len(si)
    if n==0: return 0

    sum1=sum([p1[it] for it in si])
    sum2=sum([p2[it] for it in si])

    sum1Sq=sum([pow(p1[it],2) for it in si])
    sum2Sq=sum([pow(p2[it],2) for it in si])

    pSum=sum([p1[it]*p2[it] for it in si])

    #Pearson score computation
    covariance=pSum-(sum1*sum2/n)
    stdDev=sqrt((sum1Sq-pow(sum1,2)/n)*(sum2Sq-pow(sum2,2)/n))
    if stdDev==0: return 0
    r=covariance/stdDev

    return r
################################################################################

################################################################################
#PEARSON CORRELATION SCORE
#compare correlation between p1 and p2 critics
def compareCommonTracks(p1, p2):
    si={}
    for item in p1:
        if item in p2: si[item]=1

    n=len(si)
    if n==0: return 0

    score = ((float(len(si)) / float(len(p1))) + (float(len(si)) / float(len(p2))))/2.0


    return score
################################################################################

################################################################################
def profileFollowings(client, user):
    end_page = False
    follow_href = ('users/' + str(user.id) + '/followings' )
    followers_profile = {}
    followings_count = 0
    userprof = extractProfile(client, user)
    cor = 0.0
    failcount = 0
    r= 0.0
    folcount = user.followings_count
    if folcount > 1000: folcount = 1000
    if folcount == 0: end_page = True
    while not end_page:
        while True:
            try:
                followings = client.get(follow_href, limit=100, linked_partitioning=1 )
                failcount = 0
            except:
                failcount += 1
                if failcount >5:
                    break
                continue
            break
        #followings_count += 100
        if hasattr(followings, 'next_href'):
            follow_href = followings.next_href

        for item in followings.collection:
            if end_page == False:
                followings_count +=1
                print('Progression: ' + str(int((float(followings_count)/float(folcount))*100.0)) + '%')
                buffer_profile = extractProfile(client, item, shortversion = True)
                #merge(followers_profile, buffer_profile)
                r = compareCommonTracks(buffer_profile, userprof)
                if r != 0:
                    merge(followers_profile, buffer_profile, r*r)
                if(followings_count >= folcount): end_page = True

    return followers_profile
################################################################################

################################################################################
def profileFollowingsShort(client, user):
    end_page = False
    follow_href = ('users/' + str(user.id) + '/followings' )
    followers_profile = {}
    followings_count = 0
    finalcollection = []
    userprof = extractProfile(client, user, shortversion= True, tracklimit=200)
    cor = 0.0
    failcount = 0
    r = 0
    folcount = user.followings_count
    if folcount > 300: folcount = 300
    if folcount == 0: end_page = True
    while end_page==False:
        while end_page==False:
            try:
                followings = client.get(follow_href, limit=90, linked_partitioning=1 )
                failcount = 0
            except:
                failcount += 1
                if failcount >5:
                    break
                continue
            break
        #followings_count += 100
        if hasattr(followings, 'next_href'):
            if followings.next_href != None:
                follow_href = followings.next_href
            else:
                end_page = True
        else:
            end_page = True
        [finalcollection.append(user) for user in followings.collection.data]
        if(len(finalcollection)>=folcount): break
    finalcollection = exctractsample(finalcollection)
    folcount = len(finalcollection)
    print(folcount)
    followings_count = 0
    for item in finalcollection:
        followings_count +=1
        print('Progression: ' + str(int((float(followings_count)/float(folcount))*100.0)) + '%')
        buffer_profile = extractProfile(client, item, shortversion = True, tracklimit=75, playlisting = False)
        #merge(followers_profile, buffer_profile)
        r = compareCommonTracks(buffer_profile, userprof)
        if r != 0:
            merge(followers_profile, buffer_profile, r)

    return followers_profile
################################################################################

################################################################################
def sortProfileFromFollowings(client, user):
    end_page = False
    follow_href = ('users/' + str(user.id) + '/followings' )
    followers_profile = {}
    followings_count = 0
    userprof = extractProfile(client, user)
    cor = 0.0
    failcount = 0
    r= 0.0
    folcount = user.followings_count
    if folcount > 1000: folcount = 1000
    if folcount == 0: end_page = True
    while not end_page:
        while True:
            try:
                followings = client.get(follow_href, limit=100, linked_partitioning=1 )
                failcount = 0
            except:
                failcount += 1
                if failcount >5:
                    break
                continue
            break
        #followings_count += 100
        if hasattr(followings, 'next_href'):
            follow_href = followings.next_href

        for item in followings.collection:
            if end_page == False:
                followings_count +=1
                print('Progression: ' + str(int((float(followings_count)/float(folcount))*100.0)) + '%')
                buffer_profile = extractProfile(client, item, shortversion = True)
                #merge(followers_profile, buffer_profile)
                r = compareCommonTracks(buffer_profile, userprof)
                if r != 0:
                    merge(followers_profile, buffer_profile, r*r)
                if(followings_count >= folcount): end_page = True

    return followers_profile
################################################################################

################################################################################
def merge(p1, p2, r=1):
    for key in p2:
        if p1.has_key(key):
            p1[key] += p2[key]*r
        else:
            p1[key] = p2[key]*r
################################################################################

################################################################################
def mergeExisting(p1, p2, r=1):
    for key in p2:
        if p1.has_key(key):
            p1[key] += p2[key]*r
################################################################################

################################################################################
def linkFromId(client, id, no_mix=False, played_limit = 1000000):
    try:
        track = client.get('tracks/' + id )
    except:
        print ("unable to link to track id: " + str(id))
        return 'None'

    if (track.duration > 900000 and no_mix):
        return 'None'

    if no_mix:
        if hasattr(track, 'playback_count'):
            if (track.playback_count > played_limit):
                return 'None'
        else:
            print('Ignored a track with no playback count')
            return 'None'

    return track.permalink_url
################################################################################

################################################################################
def linksFromProfile(client, profile):
    sorted_tuples = sorted(profile.items(), key=operator.itemgetter(1))
    try:
        track = client.get('tracks/' + id )
        size = len(sorted_tuples)
        listOfLinks = []
    except:
        print ("unable to link to track id: " + str(id))
        return 'None'
    l = track.duration
    if(l > 900000):
        return 'None'
    return track.permalink_url
################################################################################

################################################################################
def getSuggestionsFromProfile(client, profile, n=20, no_mix=False, played_limit = 1000000):
    sorted_tuples = sorted(profile.items(), key=operator.itemgetter(1))
    size = len(profile)
    listOfLinks = []
    name = ''
    count = 0
    fakecount = 0
    while fakecount != n and size != 0:
        name = linkFromId(client, sorted_tuples[size-1-count][0], no_mix, played_limit)
        if name != 'None':
            listOfLinks.append(name)
            fakecount += 1
            count += 1
        else:
            count += 1
    return listOfLinks
################################################################################

################################################################################
def printSuggestions(profilename):
    actualclient = register()
    user = searchForUser(actualclient, profilename)
    profile = profileFollowings(actualclient, user)
    suggestions = getSuggestionsFromProfile(actualclient, profile, 30)
    print(profilename + " should like these tracks:")
    for item in suggestions: print item
################################################################################

################################################################################
def getSuggestions(profilename):
    actualclient = register()
    user = searchForUser(actualclient, profilename)
    profile = profileFollowings(actualclient, user)
    suggestions = getSuggestionsFromProfile(actualclient, profile, 30)
    return suggestions
################################################################################

################################################################################
'''def getMostActiveUsers(client, user):
    n_user_tracks = user.track_count
    do_continue = True
    while do_continue and n_user_tracks != 0:
        while True:
            try:
                tracks = client.get(tracks_href, limit=100, linked_partitioning=1 )
                fail_number = 0
                if(hasattr(tracks, 'next_href'):
                    tracks_href = tracks.next_href
                else:
                    do_continue = False
            except:
                fail_number +=1
                print "Unexpected error:", sys.exc_info()[0]
                if(fail_number > 4):
                    do_continue = False
                    error_happened = True
                    break
                continue
            break

        for item in tracks.collection:
            print "gonthru"

################################################################################
'''

################################################################################
def getFollowerList(client, user):
    followers = []
    followers_href= 'users/' + str(user.id) + '/followers'
    while (len(followers) < user.followers_count-50):
        print('Downloading followers list: ' + str(len(followers)) + '/' + str(user.followers_count))
        try:
            followers_buffer = client.get( followers_href , limit=100, linked_partitioning=1 )
        except:
            print "Unexpected error:", sys.exc_info()[0]
            continue
        for follower in followers_buffer.collection: followers.append(follower)
        followers_href = followers_buffer.next_href
    print('Downloading followers list: ' + str(len(followers)) + '/' + str(user.followers_count))
    print('Dowloading complete')
    return followers
################################################################################

def getCommentsData(client, followers):
    data = {}
    usernames = []
    labels = []
    rownames = []
    comments = []
    comments_href = ''
    taglist = {}
    wordlist = {}
    raw_data = []
    usercount = 0
    comlimit=20
    taglimit=5
    print('Downloading comments and tags from followers...')
    for user in followers:
        comments_href = ('users/' + str(user.id) + '/comments')
        download_complete = False
        print('Advancement:'+str(usercount)+'/'+str(len(followers)))
        data[user.username] = {}
        cwordlist = []
        comcount = 0
        while not download_complete:
            try:
                comments_buffer = client.get(comments_href, limit=10, linked_partitioning=1)
            except:
                print "Unexpected error:", sys.exc_info()[0]
                continue

            for comment in comments_buffer.collection:
                comcount += 1
                try:
                    track = client.get('tracks/' + str(comment.track_id) )
                except:
                    continue
                tags = track.tag_list
                listbuffer = tags.strip().split(' ')
                ignore_next = False
                processed = False
                tagcount=0
                for i in range(0,len(listbuffer)-1):
                    if ('"' in listbuffer[i]) and ('=' not in listbuffer[i]) and not ignore_next:
                        completeword = listbuffer[i]
                        currentword=listbuffer[i+1]
                        num=1
                        while('"' not in currentword):
                            num+=1
                            completeword = completeword + currentword
                            currentword = listbuffer[i+num]
                        tagcount +=1
                        cwordlist.append(completeword.lower())
                        ignore_next = True
                        processed = True
                    elif ('=' not in listbuffer[i]) and not ignore_next:
                        cwordlist.append(listbuffer[i].lower())
                        tagcount +=1
                    elif ('"' in listbuffer[i]) and processed == False:
                        ignore_next = False
                    processed = False
                    if(tagcount >= taglimit): break

                for word in cwordlist:
                    word = word.replace('"', "")
                    word = word.replace(' ', "")
                    word = word.replace('#', "")
                    word = word.replace('-', "")
                    word = word.replace('.', "")
                    word = word.replace('_', "")
                    if data[user.username].has_key(word): data[user.username][word]+=1
                    else: data[user.username][word] = 1
                    if wordlist.has_key(word): wordlist[word]+=1
                    else: wordlist[word] = 1
            if comcount >= comlimit: download_complete = True
            if hasattr(comments_buffer, 'next_href'):
                comments_href = comments_buffer.next_href
            else:
                download_complete = True

        usercount += 1
    print('Advancement:'+str(usercount)+'/'+str(len(followers)))
    for (key,value) in wordlist.items(): labels.append(key)
    for (username, tags) in data.items():
        rownames.append(username)
        line = []
        for label in labels:
            if tags.has_key(label): line.append(tags[label])
            else: line.append(0)
        raw_data.append(line)

    return rownames,labels,raw_data

def exctractsample(followers):
    sample = []
    representativesamplesize = int(len(followers)*0.5)

    print('%s\n%s' % (len(followers), representativesamplesize))
    for i in range(representativesamplesize):
        if len(followers) != 1 :
            samplerand = random.randint(0,len(followers)-1)
            sample.append(followers[samplerand])
            followers.pop(samplerand)
        else:
            sample.append(followers[0])

    return sample
