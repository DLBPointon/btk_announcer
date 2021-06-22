from jira import JIRA
from datetime import date
import sys
import os
from dotenv import load_dotenv


def dotloader():
    load_dotenv('sample.env')
    jira_user = os.getenv('JIRA_USER')
    jira_pass = os.getenv('JIRA_PASS')
    test_hook = os.getenv('TEST_HOOK')
    prod_hook = os.getenv('PROD_HOOK')
    return jira_user, jira_pass, test_hook, prod_hook


def authorise(user, password):
    jira = "https://grit-jira.sanger.ac.uk"
    auth_jira = JIRA(jira, basic_auth=(user, password))
    return auth_jira


def labelled_btk(auth, project, decon_or_curation):
    projects = None

    if project == '= "Assembly curation"' and not decon_or_curation:
        projects = auth.search_issues(f'project {project} AND labels = BlobToolKit AND status IN (curation,"Curation QC")',
                                      maxResults=10000)

    if project == '= "Assembly curation"' and decon_or_curation:
        projects = auth.search_issues(f'project {project} AND status = Decontamination AND labels = BlobToolKit',
                                      maxResults=10000)

    if project == '= "Rapid Curation"':
        projects = auth.search_issues(f'project {project} AND labels = BlobToolKit',
                                      maxResults=10000)

    return projects


def comment_check(auth_jira, projects):
    request = []
    done = []
    running = []

    for issue in projects:
        btk_issues = auth_jira.issue(f'{issue}')
        comment_ids = btk_issues.fields.comment.comments
        for ii in comment_ids:
            comment = auth_jira.comment(f'{issue}', f'{ii}')

            if 'need a BTK' in comment.body:
                request.append(str(issue))

            if 'BTK DONE' in comment.body or 'btk done' in comment.body:
                done.append(str(issue))

            if 'BTK RUNNING' in comment.body or 'RUNNING BTK' in comment.body:
                running.append(str(issue))

    done_1, running_2, request_3 = list_setter(done, running, request)

    return done_1, running_2, request_3


def list_setter(done, running, request):
    # Creates lists of unique issues
    done = list(set(done))
    running = list(set(running))
    request = list(set(request))

    # Removes any issues found in DONE
    request = list(set(request) - set(done))
    running = list(set(running) - set(done))

    # Removes any issues found in RUNNING
    request = list(set(request) - set(running))

    return done, running, request


def list_2_output(decon, curation, rapid):

    req_start = f' --- Status == REQUESTS --- ALL CHANNELS ---'
    run_start = f' --- Status == RUNNING --- ALL CHANNELS ---'
    don_start = f' --- Status == DONE --- ALL CHANNELS ---'

    req_list = ''
    for i in decon[2], curation[2], rapid[2]:
        if not i:
            i = 'Queue Empty :+1:'

        req_list = req_list + f' {i}' + '\n'

    run_list = ''
    for i in decon[1], curation[1], rapid[1]:
        if not i:
            i = 'Queue Empty :+1:'

        run_list = run_list + f' {i}' + '\n'

    don_list = ''
    for i in decon[0], curation[0], rapid[0]:
        if not i:
            i = 'Queue Empty :+1:'

        don_list = don_list + f' {i}' + '\n'

    master_out = '{"text":"\n' + \
                 f' -------- MrBTK Report for {date.today()} START--------\n' + \
                 f' --- Version 2.0 ---\n' + \
                 f' --- Organised Decon, Curation, Rapid --- \n' + \
                 f'===================================================\n' + \
                 f'{req_start}\n' + \
                 f'{req_list}\n' + \
                 f'{run_start}\n' + \
                 f'{run_list}\n' + \
                 f'{don_start}\n' + \
                 f'{don_list}\n' + \
                 f'===================================================\n' + \
                 f' -------- Report for {date.today()} FIN -------- "' + \
                 '}'

    return master_out


def post_it(json, hook):
    webhook = f'{hook}'
    os.popen(f"curl -X POST -H 'Content-type: application/json' --data '{json}' {webhook}")


def main():
    user, password, test_hook, prod_hook = dotloader()

    auth_jira = authorise(user, password)

    project = ['= "Assembly curation"', '= "Rapid Curation"']

    decon_or_curation = [True, False]

    decon_done, decon_running, decon_request = None, None, None
    curation_done, curation_running, curation_request = None, None, None
    rapid_done, rapid_running, rapid_request = None, None, None

    for i in project:

        if i == '= "Assembly curation"':
            for ii in decon_or_curation:
                projects = labelled_btk(auth_jira, i, ii)
                if ii:
                    decon_done, decon_running, decon_request = comment_check(auth_jira, projects)
                    # Above run list_setter
                else:
                    curation_done, curation_running, curation_request = comment_check(auth_jira, projects)
                    # Above run list_setter

        else:
            projects = labelled_btk(auth_jira, i, False)

            rapid_done, rapid_running, rapid_request = comment_check(auth_jira, projects)
            # Above run list_setter

    decon = [decon_done, decon_running, decon_request]
    curation = [curation_done, curation_running, curation_request]
    rapid = [rapid_done, rapid_running, rapid_request]

    master_out = list_2_output(decon, curation, rapid)
    print(master_out)

    if sys.argv[0] == 'test':
        hook = test_hook
    else:
        hook = prod_hook

    post_it(master_out, hook)


if __name__ == '__main__':
    main()
