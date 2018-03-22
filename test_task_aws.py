#!/usr/bin/env python
"""
Required:
   boto
"""
# -*- coding: utf-8 -*-
from boto import ec2
from contextlib import closing
from datetime import datetime
import socket
from texttable import Texttable
import time
import urllib2
from aws_conn import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY 

curr_date = datetime.now()
curr_date_str = curr_date.strftime("%Y-%m-%d_%H-%M")
REGION = ec2.get_region('eu-west-1')
instance_info = []
ami_name_filter = '*rykhalskyi*'
tcp_check_port = 22

hostnames = ['sp1.kpi.in.ua', 'sp2.kpi.in.ua', 'sp3.kpi.in.ua']
publ_ip_addr_list = []
for h in hostnames:
    publ_ip_addr_list.append(socket.gethostbyname(h))

def check_tcp(host, port):
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        try:
            sock.settimeout(2)
            return sock.connect_ex((host, port)) == 0
        except socket.error as e:
            return False
        except socket.timeout as e:
            return False

def check_http(url, timeout=2):
    try:
        return urllib2.urlopen(url,timeout=timeout).getcode() == 200
    except urllib2.URLError as e:
        return False
    except socket.timeout as e:
        return False

def is_stopped(hostname):
     print "Checking state of the " + hostname
     tcp_check_status = check_tcp(hostname, tcp_check_port)
     http_check_status = check_http('http://'+ hostname)
     if tcp_check_status:
         print "TCP check for port " + str(tcp_check_port) + " is OK"
     else:
         print "TCP check for port " + str(tcp_check_port) + " has FAILED"
     if http_check_status:
         print "HTTP check is OK"
     else:
         print "HTTP check has FAILED"
     return not (tcp_check_status and http_check_status)

def create_ami(ec2conn, instance_id, ami_name, vdryRun=False):
    ami_name = ami_name + '_' + curr_date_str
    image_id = ec2conn.create_image(instance_id, ami_name, dry_run=vdryRun)
    image = ec2conn.get_all_images(image_ids=[image_id])[0]
    while image.state == 'pending':
        time.sleep(5)
        image.update()
    if image.state == 'available':
        print "AMI created succesfully"
        return True
    else:
        print "Failed to create AMI"
        return False
    

def terminate_instance(ec2conn, instance, vdryRun=False):
    print "Terminating instance " + instance
    ec2conn.terminate_instances(instance, dry_run=vdryRun)
    time.sleep(20)

def delete_old_ami(ec2conn, days_older=7, name_filter = ami_name_filter, vdryRun=False):
    count = 0
    images = ec2conn.get_all_images(owners=['self'],filters = {'name': name_filter })
    for ami in images:
        creation_date = datetime.strptime(ami.creationDate, '%Y-%m-%dT%H:%M:%S.%fZ')
        delta = curr_date - creation_date
        if delta.days > days_older:
            count += 1
            print ami.id+ " : is going to be deregistered as obsoleted."
            ami.deregister(ami.id, delete_snapshot=True, dry_run=vdryRun)
    if count == 0:
        print "No AMI older than " + str(days_older) + " days. Nothing to delete."
    else:
        print "Deleted " + str(count) + " old AMI images."

def get_target_instance_id(instances_dict, hostname):
    for i in instances_dict:
        if i.ip_address == socket.gethostbyname(hostname):
            return i.id, i.tags['Name']
    
def print_instance_info(instances_dict):
    for i in instances_dict:
        if i.ip_address in publ_ip_addr_list:
            instance_info.append({'Name': i.tags['Name'], 'id': i.id, 'private_ip': i.private_ip_address, \
                              'public_ip': i.ip_address, 'state': i.state })
    # Form a table with results
    table = Texttable()
    header = ['Name', 'ID', 'Private_IP', 'Public_IP', 'State']
    table.set_cols_width([30, 20, 15, 15, 10])
    for key in instance_info:
        table.add_rows([header, [key.get('Name'), key.get('id'),  key.get('private_ip'), key.get('public_ip'), key.get('state')]])
    print
    print table.draw()
    print

ec2conn = ec2.connection.EC2Connection(AWS_ACCESS_KEY_ID, 
                                       AWS_SECRET_ACCESS_KEY, 
                                       region = REGION)
ec2_servers = ec2conn.get_all_instances()
instances = [i for r in ec2_servers for i in r.instances]

# Checking if instance is stopped
for h in hostnames:
    if is_stopped(h):
        ec2_id, ec2_name = get_target_instance_id(instances, h)
        print "Creating AMI from stopped instance " + ec2_id
        if create_ami(ec2conn, ec2_id, ec2_name):
            terminate_instance(ec2conn, ec2_id)
        else:
            print "Stopping script script"
            break
        
#Deleting AMIs older than 7 days 
delete_old_ami(ec2conn, days_older=7)

#Printing info about instances
print_instance_info(instances)
