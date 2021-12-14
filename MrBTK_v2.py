from jira import JIRA
from datetime import date
import sys
import os
from dotenv import load_dotenv


def dotloader():
    #load_dotenv() #for testing
    jira_user = os.getenv('JIRA_USER')
    jira_pass = os.getenv('JIRA_PASS')
    test_hook = os.getenv('SLACK_TEST')
    prod_hook = os.getenv('SLACK_PROD')
    return jira_user, jira_pass, test_hook, prod_hook


def authorise(user, password):
    jira = "https://grit-jira.sanger.ac.uk"
    auth_jira = JIRA(jira, basic_auth=(user, password))
    return auth_jira


def labelled_btk(auth, project, decon_or_curation):
    projects = None

    if project == '= "Assembly curation"' and not decon_or_curation:
        projects = auth.search_issues(f'project {project} AND labels = BlobToolKit AND status IN (curation,"Curation QC", Submitted, "In Submission")',
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
    analysis = []
    rerun = []
    rerunning = []
    redone = []
    reanalysis = []

    for issue in projects:
        btk_issues = auth_jira.issue(f'{issue}')
        comment_ids = btk_issues.fields.comment.comments
        for ii in comment_ids:
            comment = auth_jira.comment(f'{issue}', f'{ii}')

            if issue.fields.labels[0] == 'BlobToolKit':
                request.append(str(issue))

            if 'BTK DONE' in comment.body or 'btk done' in comment.body:
                done.append(str(issue))

            if 'BTK RUNNING' in comment.body or 'RUNNING BTK' in comment.body:
                running.append(str(issue))

            if 'BTK ANALYSIS DONE' in comment.body or 'btk analysis done' in comment.body:
                analysis.append(str(issue))

            if "needs a new btk" in comment.body or "NEEDS A NEW BTK" in comment.body:
                rerun.append(str(issue))

            if 'BTK REDONE' in comment.body or 'btk redone' in comment.body:
                redone.append(str(issue))

            if 'BTK RERUNNING' in comment.body or 'btk rerunning' in comment.body:
                rerunning.append(str(issue))

            if 'BTK ANALYSIS REDONE' in comment.body or 'btk analysis redone' in comment.body:
                reanalysis.append(str(issue))



    analysis_1, done_1, running_2,\
    request_3, rerun_2, done_again,\
    reanalysis_2, rerunning = list_setter(analysis, done, running, request, rerun, redone, reanalysis, rerunning)

    return done_1, running_2, request_3, analysis_1, rerun_2, done_again, reanalysis_2, rerunning


def list_setter(analysis, done, running, request, rerun, redone, reanalysis, rerunning):
    # Creates lists of unique issues
    done2 = list(set(done))
    done = list(set(done)-set(analysis))
    running = list(set(running))
    request = list(set(request))

    rerun = list(set(rerun))
    redone = list(set(redone))
    rerun_2 = list(set(rerun) - set(redone))
    rerunning = list(set(rerunning))
    rerunning2 = list(set(rerunning) - set(redone))
    reanalysis_2 = list(set(redone) - set(reanalysis))

    # Removes any issues found in DONE
    request = list(set(request) - set(done2))
    running = list(set(running) - set(done2))
    analysis = list(set(analysis))

    # Removes any issues found in RUNNING
    request = list(set(request) - set(running))

    return analysis, done, running, request, rerun_2, redone, reanalysis_2, rerunning2


def list_2_output(decon, curation, rapid, analysis, rerun):

    req_start = f' --- Status == REQUESTS --- ALL CHANNELS ---'
    run_start = f' --- Status == RUNNING --- ALL CHANNELS ---'
    don_start = f' --- Status == NEED ANALYSIS --- ALL CHANNELS ---'
    reruns_start = f' --- Status == RE-RUNS --- ALL CHANNELS ---'

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

    warnings = ''
    if don_list.count('R') >= 10:
        warnings = warnings + 'Please Add {BTK ANALYSIS DONE} to finished tickets' + '\n'
    else:
        warnings = warnings
    if req_list.count('R') >= 10:
        warnings = warnings + 'Please Add {BTK DONE} to tickets' + '\n'
    else:
        warnings = warnings

    if len(warnings) > 1:
        warnings = '===================================================\n' + warnings
    else:
        warnings = warnings

    counter = 0
    for i in analysis[0], analysis[1], analysis[2]:
        for ii in i:
            counter += 1

    master_out = '{"text":"\n' + \
                 f' -------- MrBTK Report for {date.today()} START--------\n' + \
                 f' --- Version 2.4 ---\n' + \
                 f' --- Organised Decon, Curation, Rapid --- \n' + \
                 f' *Curation = Everything including and post-curation*\n' + \
                 f'===================================================\n' + \
                 f'{req_start}\n' + \
                 f'{req_list}\n' + \
                 f'{run_start}\n' + \
                 f'{run_list}\n' + \
                 f'{don_start}\n' + \
                 f'{don_list}\n' + \
                 f'{warnings}\n' + \
                 f'===================================================\n' + \
                 f'Re-Run Request: {rerun[0]},{rerun[2]},{rerun[4]}\n' + \
                 f'Re-Run Running: {rerun[9]},{rerun[10]},{rerun[11]}\n' + \
                 f'Re-Runs for Analysis: {rerun[6]},{rerun[7]},{rerun[8]}\n' + \
                 f'===================================================\n' + \
                 f'BTKed and in the Pipeline:  {counter}\n' + \
                 f'===================================================\n' + \
                 f' -------- Report for {date.today()} FIN -------- "' + \
                 '}'

    return master_out


def post_it(json, hook):
    #json = '{"text":"Why am i not working :face_with_monocle"}'
    webhook = f'{hook}'
    os.popen(f"curl -X POST -H 'Content-type: application/json' --data '{json}' {webhook}").read()
    print(json)


def main():
    user, password, test_hook, prod_hook = dotloader()

    auth_jira = authorise(user, password)

    project = ['= "Assembly curation"', '= "Rapid Curation"']

    decon_or_curation = [True, False]

    decon_analysis, curation_analysis, rapid_analysis = None, None, None
    decon_done, decon_running, decon_request, decon_re, decon_redone, decon_analysis2, decon_rerunning = None, None, None, None, None, None, None
    curation_done, curation_running, curation_request, curation_re, curation_redone, curation_analysis2, curation_rerunning = None, None, None, None, None, None, None
    rapid_done, rapid_running, rapid_request, rapid_re, rapid_redone, rapid_analysis2, rapid_rerunning = None, None, None, None, None, None, None

    for i in project:

        if i == '= "Assembly curation"':
            for ii in decon_or_curation:
                projects = labelled_btk(auth_jira, i, ii)
                if ii:
                    decon_done, decon_running, decon_request,\
                    decon_analysis, decon_re, decon_redone,\
                    decon_analysis2, decon_rerunning = comment_check(auth_jira, projects)
                    # Above run list_setter
                else:
                    curation_done, curation_running, curation_request,\
                    curation_analysis, curation_re, curation_redone,\
                    curation_analysis2, curation_rerunning = comment_check(auth_jira,projects)
                    # Above run list_setter

        else:
            projects = labelled_btk(auth_jira, i, False)

            rapid_done, rapid_running, rapid_request,\
            rapid_analysis, rapid_re, rapid_redone,\
            rapid_analysis2, rapid_rerunning = comment_check(auth_jira, projects)
            # Above run list_setter

    analysis = [decon_analysis, curation_analysis, rapid_analysis, ]
    decon = [decon_done, decon_running, decon_request, ]
    curation = [curation_done, curation_running, curation_request, ]
    rapid = [rapid_done, rapid_running, rapid_request, ]
    rerun = [decon_re, decon_redone, curation_re, curation_redone, rapid_re, rapid_redone,
             decon_analysis2, curation_analysis2, rapid_analysis2, decon_rerunning, curation_rerunning, rapid_rerunning]

    master_out = list_2_output(decon, curation, rapid, analysis, rerun)
    print(master_out)

    post_it(master_out, prod_hook)


if __name__ == '__main__':
    main()
