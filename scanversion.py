#!/usr/bin/env python
# -*- coding:utf-8 _*- 
""" 
@author:long 
@file: scanVersion.py
@time: 2018/12/10
@version: v3
@说明： 用于扫描软件版本
@v1.1:
更新tomcat,pg,httpd版本
@v1.2:
兼容python3
@v2:
更新能判断同时运行的不同版本的软件
@v3:
多版本判断规则：手动改成自动
"""

import os
import re

import subprocess


class ScanVersion:
    def __init__(self):
        self.process_name = None
        self.process_path = None
        self.version = None

        self.process_version_dict = {
            'tomcat': ['7.0.92', '8.5.35', '9.0.13'],
            'sshd': ['7.9'],
            'nginx': ['1.12.2', '1.14.2', '1.15.7'],
            'httpd': ['2.2.34', '2.4.37'],
            'mysql': ['5.7.24'],
            'redis-server': ['4.0.0'],
            'php': ['5.6.7'],
            'postgres': ['9.6.2'],
        }

    @property
    def get_process_path(self):
        """
        获得程序所在路径
        :return: process_path, [type: list]
        """
        process_path_list = []
        self.process_path = None

        cmd = "for i in `ps -ef|grep %s |grep -v grep |awk '{print $2}'`;do readlink -f /proc/$i/exe; done | uniq" % self.process_name

        if self.process_name == 'tomcat':
            cmd = "ps -ef | grep -v grep | grep 'Dcatalina.home=' | awk -F'Dcatalina.home=' '{print $2}' |grep -v '{print $2}'|awk '{print $1}' | uniq"

        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()

        if p.returncode == 0:
            out = out.decode().split('\n')  # TODO py2/3
            for process_path in out:
                if len(process_path) >= 10:
                    if self.process_name == 'tomcat':
                        process_path_list.append(process_path)
                    else:
                        process_path_list.append(os.path.dirname(process_path))

        return process_path_list

    def version_cmd(self, process_path):
        """
        根据程序名及路径，准备版本查询命令
        :return: version_cmd
        """
        if process_path:
            cmd = ['%s -V' % self.process_name, '%s -v' % self.process_name, '%s --version' % self.process_name,
                   '%s version' % self.process_name]
            # if self.path != '/usr/sbin' or self.path != '/usr/bin':

            if self.process_name == 'php':
                cmd.append('%s/* -v ' % process_path)
                cmd.append('%s/* -V ' % process_path)
                cmd.append('%s/* --version ' % process_path)
                cmd.append('%s/* version ' % process_path)

            elif self.process_name == 'tomcat':
                cmd = ['%s/bin/version.sh|grep Tomcat' % process_path]

            else:
                cmd.append('%s/%s -V ' % (process_path, self.process_name))
                cmd.append('%s/%s -v ' % (process_path, self.process_name))
                cmd.append('%s/%s --version ' % (process_path, self.process_name))
                cmd.append('%s/%s version ' % (process_path, self.process_name))
            return cmd

    def get_version(self, process_path):
        """
        获得版本
        :return: version
        """
        version = None
        for _ in self.version_cmd(process_path):
            print(_)
            p = subprocess.Popen(_, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out = str(p.communicate())

            if p.returncode == 0:
                version = ''.join(out)
                break

            elif self.process_name == 'sshd':
                version = ''.join(out)
                break

        return version

    def serialization(self, version_list, version):
        """
        序列化合格的版本及查找到的版本
        :param version_list: list[list[], ]
        :param version: list
        :return: ok_version:list, version:list
        """
        regex = re.compile(r'\d{1,2}\.\d{1,2}\.\d{0,2}')
        if self.process_name == 'sshd':
            regex = re.compile(r'\d{1,2}\.\d{1,2}')
        if self.process_name == 'postgres':
            regex = re.compile(r'\d{1,2}\.\d{1,2}\.?\d{0,2}')

        version = regex.search(version).group().strip().split('.')

        # version_list = list({i: i.split('.') for i in version_list}.values()) # python 2.6 不兼容，改下：
        version_list_dict = {}
        for i in version_list:
            version_list_dict[i] = i.split('.')

        version_list = list(version_list_dict.values())
        del version_list_dict

        return version_list, version

    def bigger(self, version, ok_version):
        """判断程序版本是否大于等于合规版本"""
        for i in range(len(ok_version)):
            if int(version[i]) > int(ok_version[i]):
                msg = '\033[1;32m%s : %s is ok \033[0m' % (self.process_name, '.'.join(version))
                return True, msg

            elif int(version[i]) < int(ok_version[i]):
                msg = '\033[1;31m%s : %s Lower than: %s \033[0m' % (
                    self.process_name, '.'.join(version), self.process_version_dict[self.process_name])
                return False, msg

            if i == len(ok_version) - 1:
                msg = '\033[1;32m%s : %s is ok \033[0m' % (self.process_name, '.'.join(version))
                return True, msg

    def check_version_list(self, version_list):
        for i in range(len(version_list) - 1):
            assert len(version_list[i]) == len(version_list[i + 1]), '\033[1;31m%s : %s 合列表格式不统一！ \033[0m' % (
                self.process_name,  self.process_version_dict[self.process_name])

    def compare_version(self, version_list, version):
        """
        判断程序版本属于哪条产品线，交给bigger()比较大小
        :param version_list:
        :param version:
        :return: ok_version, version [type, list]
        """
        # 序列化
        version_list, version = self.serialization(version_list, version)

        # 1、对于只有一个版本的程序，直接比较
        if len(version_list) == 1:
            return self.bigger(version, version_list[0])
        else:
            self.check_version_list(version_list)

        # 2、对于比每一个合规版本都大的，返回True
        n = 0
        for ok_version in version_list:
            result, msg = self.bigger(version, ok_version)
            if result:
                n += 1
            if n == len(version_list):
                return result, msg

        # 3、在合规版本里，直接返回True; 如果版本长度少于3，例如['7.8', '8.0'], 要求版本完全等于合规版本
        if version in version_list:
            return self.bigger(version, version)
        elif len(version_list[0]) < 3:
            return False, '\033[1;31m%s : %s is not in  %s \033[0m' % (
                self.process_name, '.'.join(version), self.process_version_dict[self.process_name])

        # 4、比较版本列表之间的不同点（key num）；例如：['8.5.92', '8.5.35', '10.0.13']，key是最后一位（93,35,13）的index.如果版本在这些版本列表的key word
        # 中，说明版本属于这个合规版本, 对版本和合规版本进行大小比较
        diff_version_num_list, diff_key = None, None
        for key in range(len(version_list[0])):
            diff_version_num_list = [i[key] for i in version_list]
            if len(set(diff_version_num_list)) >= len(version_list):
                diff_key = key
                break
        if diff_key is not None:
            for ok_version in version_list:
                if version[diff_key] == ok_version[diff_key]:
                    return self.bigger(version, ok_version)

        return False, '\033[1;31m%s : %s is not in  %s \033[0m' % (
            self.process_name, '.'.join(version), self.process_version_dict[self.process_name])

    def run(self):
        for process_name in self.process_version_dict.keys():
            print('\n')
            print('########## Scanning  ' + process_name + ' ##########')

            self.process_name = process_name
            process_path_list = self.get_process_path

            if process_path_list:
                msg = {}
                for process_path in process_path_list:
                    version = self.get_version(process_path)
                    if version:
                        _, msg[process_path] = self.compare_version(self.process_version_dict[process_name], version)
                    else:
                        msg[process_path] = (
                                '\033[1;33m Cannot find %s version : Permission denied, Running in docker? \033[0m' % process_name)

                # 打印结果
                for _ in msg.keys():
                    print(msg[_])

            else:
                print('\033[1;32m%s is not running \033[0m' % process_name)

    def test(self):
        self.process_name = 'tomcat'

        def my_assert(fc, bool=True):
            assert fc[0] is bool
            # print(fc[1])

        my_assert(self.compare_version(['7.8.1'], '1.1.8'), False)
        my_assert(self.compare_version(['7.8.1'], '7.8.1'), True)
        my_assert(self.compare_version(['7.8.1', '9.1.1'], '6.8.1'), False)
        my_assert(self.compare_version(['7.8.1', '9.1.1'], '7.8.1'), True)
        my_assert(self.compare_version(['7.8.1', '9.1.1'], '10.7.8'), True)
        my_assert(self.compare_version(['7.8.1', '8.1.1', '9.1.1'], '6.1.8'), False)
        my_assert(self.compare_version(['7.8.1', '8.1.1', '9.1.1'], '9.1.1'), True)
        my_assert(self.compare_version(['7.8.1', '8.1.1', '9.1.1'], '9.1.8'), True)
        my_assert(self.compare_version(['7.8.1', '7.8.5', '9.1.1'], '7.8.0'), False)
        my_assert(self.compare_version(['7.8.1', '7.8.5', '9.1.1'], '7.8.5'), True)
        my_assert(self.compare_version(['7.8.1', '7.8.5', '9.1.1'], '7.8.6'), False)
        my_assert(self.compare_version(['7.8.1', '7.8.5', '9.1.1'], '10.8.4'), True)
        my_assert(self.compare_version(['7.7.1', '7.8.5', '9.1.1'], '7.7.0'), False)
        my_assert(self.compare_version(['7.7.1', '7.8.5', '9.1.1'], '7.8.6'), True)
        my_assert(self.compare_version(['7.7.1', '8.8.5', '9.1.1'], '7.8.6'), True)  # todo

        self.process_name = 'sshd'

        my_assert(self.compare_version(['7.8'], '0.0'), False)
        my_assert(self.compare_version(['7.8'], '7.0'), False)
        my_assert(self.compare_version(['7.8'], '7.8'), True)
        my_assert(self.compare_version(['7.8'], '8.9'), True)
        my_assert(self.compare_version(['7.8', '8.0'], '7.0'), False)
        my_assert(self.compare_version(['7.8', '8.0'], '7.8'), True)
        my_assert(self.compare_version(['7.8', '8.0'], '8.0'), True)
        my_assert(self.compare_version(['7.8', '8.0'], '9.1'), True)
        my_assert(self.compare_version(['7.8', '8.0'], '7.9'), False)
        # my_assert(self.compare_version(['7.8.1', '8.0'], '7.9'), True)


if __name__ == '__main__':
    sv = ScanVersion()
    sv.test()  # 修改程序后，请去掉注释，进行测试
    sv.run()
