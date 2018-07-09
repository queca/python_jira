#!/usr/bin/env python

"""
DESCRIPTION

    A script to create a (group) release ticket (REL-*) on JIRA containing all the tickets for the versions in the list
    passed as argument.

     => Compulsory args <=

     [-u,--user] User to connect to Jenkins server to fetch the release.log. Only users who access to corp servers can
                 execute this script locally.

     [-k,--keys] Location of your private key to ssh to Jenkins server

     [-s,--summary] Short summary of the release ticket

     [-c,--current] Path to the current json file containing the version to be deployed

     [-p,--previous] Path to the  json file containing the version deployed on the environment

     [-e,--env] environment


     => Optional args <=
     [-r,--released] Flag to release all the versions in the list on Jira(X project). Default to false, to enable this
                     just pass -r


USAGE
    ./releaseJira.py --user raquelc --keys /home/.ssh/id_rsa \
    --summary Release sprint 30 -r

    ./releaseJira.py -  "backend-srv_3.0.1" --user queca --keys /home/.ssh/id_rsa
    --summary Release for enabling X-box Games -r

AUTHOR
    quelribeiro@gmail.com

"""
import paramiX
import re
import argparse
import requests
import json
import sys
from jira import JIRA


JIRA_URL = 'https://yourcompany.atlassian.net/'
OPTIONS = {'server': JIRA_URL}

# parse arguments
parser = argparse.ArgumentParser()

parser.add_argument('-u', '--user', help='User performing the release', required=True)

parser.add_argument('-k', '--keys', help='ssh key to connect to a server in corp network', required=True)

parser.add_argument('-s', '--summary', help='Summary of release ticket', required=True)

parser.add_argument('-c', '--current', help='Current json containing the version to be deployed', required=True)

parser.add_argument('-p', '--previous', help='Previous json containing versions deployed on the environment',
                    required=True)

parser.add_argument('-e', '--environment', help='environment', required=True)

parser.add_argument('-r', '--released', action='store_true', dest='releasedVersion',
                    help='Released all the versions on Jira X project')

args = parser.parse_args()


def create_release_list(previous, current):

    # parse the current and previous deploy.json to find out the changes

    source = {
        "backend-srv": "backend-source",
        "frontend-srv": "frontend-source"
    }

    with open(previous) as previous_deploy, open(current) as current_deploy:
        previous = json.load(previous_deploy)
        current = json.load(current_deploy)
        release_list = set()

        for i in range(0, len(current['deployment'])):
            for y in range(0, len(previous['deployment'])):

                if ((current['deployment'][i]['name'] == previous['deployment'][y]['name']) and \
                        (current['deployment'][i]['version'] != previous['deployment'][y]['version'])):

                    print(" {} {} -->  {} ".format(previous['deployment'][y]['name'],
                                                   previous['deployment'][y]['version'],

                                                   current['deployment'][i]['version']))

                    release_list.add (source[current['deployment'][i]['name']] + "-" +
                                      current['deployment'][i]['version'].replace(".RELEASE", ""))
    # print(release_list)
    return release_list


def fetch_release_log(user, keys):
    try:
        # ssh to Jenkins to get the release.log
        ssh = paramiX.SSHClient()
        ssh.load_system_host_keys()
        ssh.connect(hostname='jenkins.yourdomain.com', port=22, username=user, key_filename=keys)

        scp = ssh.open_sftp()
        # location of your release.log
        scp.get('/jenkins_data/release.log', 'release.log')
        scp.close()

    except Exception as err:
        print ('[ERROR] Not possible to connect to jenkins.yourdomain.com:' + str(err))
        sys.exit(1)


def release_ticket(summary, apps_released, env):
    # Create release ticket
    ticket = jira.create_issue(project='REL', summary="Release of {} on {}".format(summary, env),
                               description='Automatically created by DevOps build team \n triggered by ' +
                                           args.user + '\n', issuetype={'name': 'Task'})

    print('[JIRA]: Release ticket: {}/browse/{}:'.format(JIRA_URL, ticket))

    issue = jira.issue(ticket)
    issue_description = issue.fields.description + '\n'

    update = issue_description + '\n'

    found = set()

    # Read release.log to find out REL-tickets of apps
    with open('release.log', 'rt') as in_file:

        for line in in_file:
            for app in apps_released:

                if app in line:
                    print
                    app_release_ticket = re.match(r'^REL-[\d]+', line)
                    print('[JIRA]:  -->:{} '.format(line))

                    if app_release_ticket:
                        update += line + '\n'
                        found.add(app)

    # Update ticket description with all app's REL-tickets
    issue.update(description=update)

    # Check if a version doesn't exist on Jira
    print(found)
    for app in apps_released:
        if app not in found:
            print('[WARNING] {} not found in Release log'.format(app))


def release_version(apps_released):
    versions = jira.project_versions('X')
    found = set()

    for version in versions:

        for app in apps_released:

            # Replace '-' to '_' to match Jira version pattern <service>_<number>
            app = re.sub(r'(-)([0-9]+.[0-9]+.[0-9]+)', r'_\2', app)

            if app == version.name:

                # I couldn't find out how to update version using jira-python, had to use REST API
                body = {
                    "id": version.id,
                    "released": False,
                    "description": "Transition performed by DevOps team triggered by :" + args.user
                }

                data = json.dumps(body)
                headers = {'Content-type': 'application/json', 'Accept': 'application/json'}

                r = requests.put("{}rest/api/2/version/{}".format(JIRA_URL, version.id),
                                 data, auth=('user', 'password'), headers=headers)

                # TO-DO treat the exceptions here !

                if r.status_code == 200:
                    # added app to a set()
                    found.add(app)

                    print(r.status_code)
                    print('[JIRA] {} "released" on Jira'.format(version.name))

    for app in apps_released:
        app = re.sub(r'(-)([0-9]+.[0-9]+.[0-9]+)', r'_\2', app)

        if app not in found:
            print('[WARNING] {} not found on Jira X project'.format(app))


def main():
    global args
    global jira

    released_list = create_release_list(args.previous, args.current)

    jira = JIRA(OPTIONS, basic_auth=('user', 'password'))

    # Fetch release.log from Jenkins server
    fetch_release_log(args.user, args.keys)

    # Create the Release ticket with all apps to be released
    release_ticket(args.summary, released_list, args.environment)

    # Release all the app's versions on X project on Jira
    if args.releasedVersion:
        release_version(released_list)


if __name__ == '__main__':
    main()