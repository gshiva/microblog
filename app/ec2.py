import boto.ec2

def share_image(aws_acct_id, image_id):
    conn = boto.ec2.connect_to_region("us-west-2",
           aws_access_key_id = 'AKIAJ2QS3U5R6WBLOG7A',
           aws_secret_access_key = '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')
    image = conn.get_image(image_id)
    return image.set_launch_permissions([str(aws_acct_id)])