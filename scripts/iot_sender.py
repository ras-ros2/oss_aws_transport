#!/usr/bin/env python3

"""
Copyright (C) 2024 Harsh Davda

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.

For inquiries or further information, you may contact:
Harsh Davda
Email: info@opensciencestack.org
"""

import rclpy
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory
import json
import time
from ras_interfaces.action import ExecuteExp
from std_srvs.srv import SetBool
from rclpy.action import ActionServer
from rclpy.callback_groups import ReentrantCallbackGroup
from std_msgs.msg import Bool
from ras_interfaces.msg import Instruction
import ast
from trajectory_msgs.msg import JointTrajectory
# from awscrt import mqtt 
import json
# from connection_helper import ConnectionHelper
from ras_interfaces.srv import SetPath
from ras_interfaces.action import ExecuteExp
from ras_common.transport.TransportServer import TransportMQTTPublisher
import os
import zipfile



class LinkHandler(Node):

    def __init__(self):
        super().__init__('link_sender')

        my_callback_group = ReentrantCallbackGroup()

        self.declare_parameter("path_for_config", "")
        self.declare_parameter("discover_endpoints", False)
        self.client = self.create_client(SetPath, "/send_file", callback_group=my_callback_group)
        self.send_client = ActionServer(self, ExecuteExp, "/execute_exp", self.send_callback, callback_group=my_callback_group)

        self.ws_path = os.environ["RAS_WORKSPACE_PATH"]
        # self.path_for_config = os.path.join(self.ws_path, "src", "ras_aws_transport", "aws_configs", "iot_sender_config.json")
        discover_endpoints = False
        # self.connection_helper = ConnectionHelper(self.get_logger(), self.path_for_config, discover_endpoints)
        self.mqtt_pub = TransportMQTTPublisher("test/topic")
        self.connect_to_aws()
        
    def connect_to_aws(self):
        """Attempt to connect to AWS IoT with retries"""
        while True:
            try:
                self.mqtt_pub.mqttpublisher.connect()
                self.get_logger().info("Connected to AWS IoT")
                break
            except Exception as e:
                self.get_logger().error(f"Connection to AWS IoT failed: {e}. Retrying in 5 seconds...")
                time.sleep(5)

    def send_callback(self, goal_handle):
        self.get_logger().info("Starting Real Arm.....")
        zip_file_path = self.zip_xml_directory()
        path = os.path.join(self.ws_path, "src", "ras_bt_framework", "xml", "xml_directory.zip")
        self.send_zip_file_path(path)
        result = ExecuteExp.Result()
        result.success = True
        goal_handle.succeed()
        return result
        
    def send_zip_file_path(self, zip_file_path):
        request = SetPath.Request()
        request.path = zip_file_path
        
        self.client.wait_for_service()
        future = self.client.call_async(request)

        rclpy.spin_until_future_complete(self, future)
        response = future.result()
        print(response.link)
        self.publish_with_retry(response.link)

    def zip_xml_directory(self):
    # Get the directory of the current script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Define the path to the xml directory
        xml_dir_path = "/ras_sim_lab/ros2_ws/src/ras_bt_framework/xml/"
        
        # Define the path for the output zip file
        zip_file_path = "/ras_sim_lab/ros2_ws/src/ras_bt_framework/xml/xml_directory.zip"
        
        # Create a zip file and add all files in the xml directory to it
        with zipfile.ZipFile(zip_file_path, 'w') as zipf:
            for root, dirs, files in os.walk(xml_dir_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, start=xml_dir_path)
                    zipf.write(file_path, arcname)
        
        return zip_file_path

    def publish_with_retry(self, payload, delay=2):
        self.get_logger().info("Publishing to AWS IoT")
        self.mqtt_pub.mqttpublisher.publish(payload.encode("utf-8"))
        # self.connection_helper.mqtt_conn.publish(
        #     topic="test/topic",
        #     payload=payload,
        #     qos=mqtt.QoS.AT_LEAST_ONCE
        # )

        time.sleep(0.25)

def main(args=None):
    rclpy.init(args=args)
    node = LinkHandler()
    try:
        while rclpy.ok():
            rclpy.spin_once(node)
            node.mqtt_pub.mqttpublisher.client.loop()

    except KeyboardInterrupt:
        pass
    finally:
        # Cleanup and disconnect
        node.destroy_node()
        node.get_logger().info("Disconnected from AWS IoT")
        rclpy.shutdown()

if __name__ == '__main__':
    main()
