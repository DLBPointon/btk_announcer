from jira import JIRA
from datetime import date
import os
from dotenv import load_dotenv
from tabulate import tabulate
import pandas as pd
import requests
import time

startTime = time.time()

BTK_STATUS = ['BTK DONE', 'btk done',
                'BTK RUNNING', 'RUNNING BTK',
                'good to'
                'needs a new btk', 'NEEDS A NEW BTK',
                'BTK REDONE', 'btk redone',
                'BTK RERUNNING', 'btk rerunning']
END_LIST = ['BTK ANALYSIS DONE', 'btk analysis done',
            'BTK ANALYSIS REDONE', 'btk analysis redone']

def dotloader():
    load_dotenv() #for testing
    jira_user = os.getenv('JIRA_USER')
    jira_pass = os.getenv('JIRA_PASS')
    test_hook = os.getenv('SLACK_TEST')
    prod_hook = os.getenv('SLACK_PROD')
    return jira_user, jira_pass, test_hook, prod_hook


def authorise(user, password):
    return JIRA("https://grit-jira.sanger.ac.uk", basic_auth=(user, password))

def dict_add(ticket_dict, ticket_list, project, decon_or_curation):
    for i in ticket_list:
        ticket_dict[str(i)] = {'project': project, 'decon_or_curation': decon_or_curation}
    return ticket_dict

def labelled_btk(auth, project, decon_or_curation):
    tickets = {}

    for i in project:
        for ii in decon_or_curation:
            if i == "Assembly curation" and not ii:
                ticket_list = auth.search_issues(f'project ="{i}" AND labels = BlobToolKit AND status IN (curation,"Curation QC", Submitted, "In Submission")',
                                                maxResults=10000)
                tickets = dict_add(tickets, ticket_list, i, ii)

            if i == "Assembly curation" and ii:
                ticket_list = auth.search_issues(f'project ="{i}" AND status = Decontamination AND labels = BlobToolKit',
                                                maxResults=10000)
                tickets = dict_add(tickets, ticket_list, i, ii)

            if i == "Rapid Curation":
                ticket_list = auth.search_issues(f'project ="{i}" AND labels = BlobToolKit',
                                                maxResults=10000)
            tickets = dict_add(tickets, ticket_list, i, ii)
    return tickets

def comment_check(auth_jira, tickets):
    del_list = []

    for x, y in tickets.items():
        i = auth_jira.issue(f'{x}')
        for z in i.fields.labels:
            if 'BlobToolKit' in z:
                for ii in i.fields.comment.comments:
                    comment = auth_jira.comment(f'{x}', f'{ii}')
                    if any(s in comment.body for s in END_LIST):
                        del_list.append(str(x))
                    else:
                        for i in BTK_STATUS:
                            if i in comment.body:
                                y['btk_status'] = i

            else:
                pass

    for i in del_list:
        if i in tickets:
            del tickets[i]
    
    return tickets

def add_assignee(auth, tickets):
    for x, y in tickets.items():
        i = auth.issue(f'{x}')
        y['assignee'] = i.fields.assignee
        y['stat'] = i.fields.status
    return tickets

def convert_to_df(ticket_dict):
    return pd.DataFrame.from_dict(ticket_dict) 


def main():    
    user, password, test_hook, prod_hook = dotloader()
    auth_jira = authorise(user, password)

    project = ["Assembly curation", "Rapid Curation"]
    decon_or_curation = [True, False]

    tickets = labelled_btk(auth_jira, project, decon_or_curation)
    pending_tickets = comment_check(auth_jira, tickets)
    assigned_tickets = add_assignee(auth_jira, pending_tickets)
    df = convert_to_df(assigned_tickets)
    df = df.T
    df['btk_status'] = df['btk_status'].fillna('BTK REQUESTED')
    df['btk_sorter'] = df['btk_status'].str.len()
    df.sort_values(['btk_sorter'], axis=0, inplace=True, ascending=False)
    df.drop(columns=['decon_or_curation','btk_sorter'], inplace=True)
    prettier_df = tabulate(df, tablefmt = "grid", headers=['Ticket ID', 'Queue', 'Assignee', 'Ticket Status', 'BTK status'])
    executionTime = (time.time() - startTime)

    headers = {
        'Content-Type': 'application/json',
            }

    data = '{"text":' + "'Report for: " + str(date.today().strftime('%d-%b-%Y')) + " \n ```" + str(prettier_df) + "``` \n I took: " + str(round(executionTime)) + " seconds'" + '}'

    res = requests.post( prod_hook, headers=headers, data=data)
    print(res)

if __name__ == '__main__':
    main()
