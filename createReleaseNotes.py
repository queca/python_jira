#!/usr/bin/env python

""" This script will generate a confluence page with a JIRA filter based on label passed as argument.
labels can be: RY(YEAR), RM(YEAR.MONTH) , RW(YEAR.WEEK)
"""

import requests
import json
import datetime
import argparse
import sys

# parse arguments
parser = argparse.ArgumentParser()
parser.add_argument("--f", action="store", dest="filter", help="filter ", required=True, choices=['year', 'month',
                                                                                                  'week'] )
parser.add_argument("--l", action="store", dest="label", help="Release label(s)", required=True, type=int)
parser.add_argument("--e", action="store", dest="env", help="Environment", required=True)

args = parser.parse_args()

def releaseLabel(filter,label):

    """function to validate arguments and  return a valid JIRA label"""

    year = [2018]
    month = list(range(1,13))
    week = list(range(1,53))

    today = datetime.datetime.now()
    currentYear =  today.strftime("%Y")

    # Check Year
    if filter == "year" and label not in year:
       print("This is not a valid year")
       sys.exit()
    elif filter == "year" and label in year:
        return "RY.{}".format(label)

    # Check Month
    if filter == "month" and label not in month:
        print( "This is not a valid month")
        sys.exit()
    elif filter == "month" and label in month:
        return "RM.{}.{}".format(currentYear, str(label).zfill(2))

    # Check week
    if filter == "week" and label not in week:
        print("This is not a valid work week")
        sys.exit()
    elif filter == "week" and label in week:
        return "RW.{}.{}".format(currentYear, str(label).zfill(2))


def printResponse(response):

    """function to print a JSON file in a nice format to allow easy identification of nodes """

    print('{} {}\n'.format(json.dumps(response.json(), sort_keys=True, indent=4, separators=(',', ': ')), response))


def createReleaseNotes(env, label):

    """function to send a post request to Confluence API to create a new content.
       At the end of the request it will print the URL of the new page.
    """

    #SRE team space id
    confluence_id = "<confluenceID>"
    confluence_url = "https://<confluenceURL>/wiki/rest/api/content"

    today = datetime.datetime.now()

    release_title = env.replace('RE.','') + " Release Notes " + today.strftime("%Y-%m-%d")


    html_body="<p><ac:structured-macro ac:name=\"jira\" ac:schema-version=\"1\" " \
              "ac:macro-id=\"026b3ee7-3e57-4eb9-bd8e-bb502eb30476\">" \
              "<ac:parameter ac:name=\"columns\">key,components,summary,status,fixversions,epic link </ac:parameter>" \
              "<ac:parameter ac:name=\"jqlQuery\">labels = {} AND labels = {} ORDER BY {epicID}</ac:parameter>" \
              "</ac:structured-macro></p>".format(env, label)
    body = {
        "ancestors": [{"id": confluence_id}],
        "body": {
            "editor2": {
                "representation": "editor2",
                "value" : html_body
            }
        },
        "space": {
            "key": "SRE"
        },
        "status": "current",
        "title": release_title ,
        "type": "page"
    }

    data = json.dumps(body)
    headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
    r = requests.post(confluence_url, data, auth=('user', 'password'), headers=headers)

    if r.status_code == 400:
        payload = {'spaceKey': 'SR', 'title': release_title }
        r2 = requests.get(confluence_url , params=payload , auth=('user', 'passowrd'), headers=headers)
        if r2.status_code != 200:
            print(" [ERROR] Response code: {}".format(r.status_code))
            sys.exit(1)
        response_dict = r2.json()
        print ("Page already existed at : "
               "https://confluenceURL.atlassian.net/wiki/spaces/SR/pages/{}").format(response_dict["results"][0]["id"])
        sys.exit(1)
    elif r.status_code == 200:
        response_dict = r.json()
        print ("Release Notes links : "
               "https://confluenceURL.atlassian.net/wiki{}").format(response_dict["_links"]["webui"])
    else:
        print(" [ERROR] Response code: {}".format(r.status_code))
        sys.exit(1)

def main():

    label = releaseLabel(args.filter, args.label)
    # print(label)
    release_env = "RE.{}".format(args.env)
    # print(release_env)
    createReleaseNotes(release_env, label)

if __name__ == "__main__":
    main()
