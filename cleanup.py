#!/usr/bin/env python3

import boto3
import time
import sys


def cleanup_rds(region, skip_final_snapshot=True, delete_auto_backup=True):
    client = boto3.client("rds", region_name=region)
    for instance in client.describe_db_instances()["DBInstances"]:
        if instance["DeletionProtection"]:
            response = client.modify_db_instance(
                DBInstanceIdentifier=instance["DBInstanceIdentifier"],
                DeletionProtection=False
            )
        response = client.delete_db_instance(
            DBInstanceIdentifier=instance["DBInstanceIdentifier"],
            SkipFinalSnapshot=skip_final_snapshot,
            DeleteAutomatedBackups=delete_auto_backup
        )
        deleted_waiter = client.get_waiter("db_instance_deleted")
        print("waiting RDS instance {} deleted ...".format(instance["DBInstanceIdentifier"]), file=sys.stderr)
        deleted_waiter.wait(DBInstanceIdentifier=instance["DBInstanceIdentifier"])


def cleanup_ec2(region):
    client = boto3.client("ec2", region_name=region)
    instance_ids = list()
    for reservation in client.describe_instances()["Reservations"]:
        for instance in reservation["Instances"]:
            instance_ids.append(instance["InstanceId"])
    if instance_ids:
        print("deleting EC2 instance {} ...".format(instance_ids), file=sys.stderr)
        response = client.terminate_instances(InstanceIds=instance_ids)


def cleanup_elbv2(region):
    client = boto3.client("elbv2", region_name=region)
    load_balancer_arns = list(lb["LoadBalancerArn"] for lb in client.describe_load_balancers()["LoadBalancers"])
    for load_balancer_arn in load_balancer_arns:
        client.delete_load_balancer(LoadBalancerArn=load_balancer_arn)
    if load_balancer_arns:
        deleted_waiter = client.get_waiter("load_balancers_deleted")
        print("waiting ALB {} deleted ...".format(load_balancer_arns), file=sys.stderr)
        deleted_waiter.wait(LoadBalancerArns=load_balancer_arns)
        time.sleep(10)
    for target_group in client.describe_target_groups()["TargetGroups"]:
        client.delete_target_group(TargetGroupArn=target_group["TargetGroupArn"])


def cleanup_vpc(region):
    filters = [{"Name": "isDefault", "Values": ["false"]}]
    client = boto3.client("ec2", region_name=region)
    for vpc in client.describe_vpcs(Filters=filters)["Vpcs"]:
        vpc_cleanup(vpc["VpcId"], region)
        # filters = [{"Name":"vpc-id","Values":[vpc["VpcId"]]}]
        # for sg in client.describe_security_groups(Filters=filters)["SecurityGroups"]:
        #     if sg["GroupName"]  == "default":
        #         continue
        #     response = client.delete_security_group(GroupId=sg["GroupId"])
        # for subnet in client.describe_subnets(Filters=filters)["Subnets"]:
        #     response = client.delete_subnet(SubnetId=subnet["SubnetId"])
        # for route_table in client.describe_route_tables(Filters=filters)["RouteTables"]:
        #     response = client.delete_route_table(RouteTableId=route_table["RouteTableId"])
        # for nat_gateway in client.describe_nat_gateways(Filters=filters)["NatGateways"]:
        #     respones = client.delete_nat_gateway(NatGatewayId=nat_gateway["NatGatewayId"])
        #     print("waiting NatGateway {} deleted ...".format(nat_gateway["NatGatewayId"]), file=sys.stderr)
        #     wait_nat_gateway_deleted(region, nat_gateway["NatGatewayId"])
        # print("deleting VPC {} ...".format(vpc["VpcId"]), file=sys.stderr)
        # client.delete_vpc(VpcId=vpc["VpcId"])


def vpc_cleanup(vpcid,region):
    """Remove VPC from AWS
    Set your region/access-key/secret-key from env variables or boto config.
    :param vpcid: id of vpc to delete
    """
    if not vpcid:
        return
    print('Removing VPC ({}) from AWS'.format(vpcid))
    ec2 = boto3.resource('ec2',region_name=region)
    ec2client = ec2.meta.client
    vpc = ec2.Vpc(vpcid)
    # detach default dhcp_options if associated with the vpc
    dhcp_options_default = ec2.DhcpOptions('default')
    if dhcp_options_default:
        dhcp_options_default.associate_with_vpc(
            VpcId=vpc.id
        )
    # detach and delete all gateways associated with the vpc
    for gw in vpc.internet_gateways.all():
        vpc.detach_internet_gateway(InternetGatewayId=gw.id)
        gw.delete()
    # delete all route table associations
    for rt in vpc.route_tables.all():
        for rta in rt.associations:
            if not rta.main:
                rta.delete()
    for rt in vpc.route_tables.all():
         if not rt.associations[0].main
            rt.delete()
    # delete any instances
    for subnet in vpc.subnets.all():
        for instance in subnet.instances.all():
            instance.terminate()
    # delete our endpoints
    for ep in ec2client.describe_vpc_endpoints(
            Filters=[{
                'Name': 'vpc-id',
                'Values': [vpcid]
            }])['VpcEndpoints']:
        ec2client.delete_vpc_endpoints(VpcEndpointIds=[ep['VpcEndpointId']])
    # delete our security groups
    for sg in vpc.security_groups.all():
        if sg.ip_permissions:
            sg.revoke_ingress(IpPermissions=sg.ip_permissions)
        if sg.ip_permissions_egress:
            sg.revoke_egress(IpPermissions=sg.ip_permissions_egress)
    for sg in vpc.security_groups.all():
        if sg.group_name != 'default':
            sg.delete()
    # delete any vpc peering connections
    for vpcpeer in ec2client.describe_vpc_peering_connections(
            Filters=[{
                'Name': 'requester-vpc-info.vpc-id',
                'Values': [vpcid]
            }])['VpcPeeringConnections']:
        ec2.VpcPeeringConnection(vpcpeer['VpcPeeringConnectionId']).delete()
    # delete non-default network acls
    for netacl in vpc.network_acls.all():
        if not netacl.is_default:
            netacl.delete()
    # delete network interfaces
    for subnet in vpc.subnets.all():
        for interface in subnet.network_interfaces.all():
            interface.delete()
        subnet.delete()
    # finally, delete the vpc
    ec2client.delete_vpc(VpcId=vpcid)


def cleanup_nat_gateway(region):
    filters = [{"Name": "isDefault", "Values": ["false"]}]
    client = boto3.client("ec2", region_name=region)
    for vpc in client.describe_vpcs(Filters=filters)["Vpcs"]:
        filters = [{"Name":"vpc-id","Values":[vpc["VpcId"]]}]
        for nat_gateway in client.describe_nat_gateways(Filters=filters)["NatGateways"]:
            respones = client.delete_nat_gateway(NatGatewayId=nat_gateway["NatGatewayId"])
            print("deleting NatGateway {}...".format(nat_gateway["NatGatewayId"]), file=sys.stderr)


def wait_nat_gateway_deleted(region,nat_gateway_id):
    client = boto3.client("ec2", region_name=region)
    nat_gateway = client.describe_nat_gateways(NatGatewayIds=[nat_gateway_id])["NatGateways"][0]
    while nat_gateway:
        eni_id = nat_gateway["NatGatewayAddresses"][0]["NetworkInterfaceId"]
        eni = client.describe_network_interfaces(NetworkInterfaceIds=[eni_id])
        if not eni:
            break
        time.sleep(15)

def cleanup_eip(region):
    client = boto3.client("ec2", region_name=region)
    for eip in client.describe_addresses()["Addresses"]:
        if eip.get("NetworkInterfaceId"):
            continue
        print("releasing EIP {} ...".format(eip["PublicIp"]), file=sys.stderr)
        client.release_address(AllocationId=eip["AllocationId"])


def main():
    ec2 = boto3.client("ec2")
    regions = map(lambda x: x["RegionName"], ec2.describe_regions()["Regions"])

    for region in regions:
        print("in Region {} ... Delete NatGateways".format(region), file=sys.stderr)
        cleanup_nat_gateway(region)

    regions = map(lambda x: x["RegionName"], ec2.describe_regions()["Regions"])
    for region in regions:
        print("in Region {} ...".format(region), file=sys.stderr)
        cleanup_rds(region)
        cleanup_ec2(region)
        cleanup_elbv2(region)
        cleanup_vpc(region)
        cleanup_eip(region)


if __name__ == "__main__":
    main()
