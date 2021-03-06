#!/usr/bin/python
import sys, json, glob, os, mysql.connector, re, influxdb
from datetime import datetime, date, timedelta
from mysql.connector import errorcode
from pprint import pprint, pformat
import logging

def setup_logger(logger_name, log_file, level=logging.INFO) :# {{{
  l = logging.getLogger(logger_name)
  formatter = logging.Formatter('%(asctime)s : %(message)s')
  fileHandler = logging.FileHandler(log_file, mode='w')
  fileHandler.setFormatter(formatter)
  streamHandler = logging.StreamHandler()
  streamHandler.setFormatter(formatter)

  l.setLevel(level)
  l.addHandler(fileHandler)
  l.addHandler(streamHandler)    
# }}}

influx = influxdb.InfluxDBClient('localhost', 8086, '', '', 'gomlog')
BIN_PATH = os.path.dirname(os.path.realpath(__file__)) + '/'

config = {# {{{
  'host': '127.0.0.1',
  'user': 'root',
  'password': '',
  'database': '',
  'autocommit' : True,
  'get_warnings': True,
  'raise_on_warnings': True,
  #'use_pure': False,
}# }}}

tableLog = 'archive_event'
tableStat = 'prd_daily_stat'

with open(BIN_PATH+'../config/tf.json') as default_file:    
  default = json.load(default_file)

try:# {{{
  config['host'] = default['mysql']['host']
  config['user'] = default['mysql']['user']
  config['password'] = default['mysql']['password']
  config['database'] = default['mysql']['database']
  cnx = mysql.connector.connect(**config)
  cursor = cnx.cursor() #prepared=True
  cursor.execute('SET sql_log_bin = 0')
except mysql.connector.Error as err:
  if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
    print("Something is wrong with your user name or password")
  elif err.errno == errorcode.ER_BAD_DB_ERROR:
    print("Database does not exist")
  else:
    print(err)
    exit(1)
# }}}

def insert2mysql(prod,row) :

  sql='''INSERT INTO prd_daily_stat 
    ( d, product, action, cc2, tot, uni )
    ( %s, %s, %s, %s, %d, %d )'''
  try :
    print row
    exit(1)
    cursor.execute(sql)
  except mysql.connector.Error as err:
    log_daily.error( pformat([err,sql], indent=4) )

def import_stat (d, prod, pat) :
  table = 'events_'+ 'player' if prod=='player' else 'etc'
  dt_start = str(d)+'T00:00:00Z'
  dt_end = str(d+timedelta(days=1))+'T00:00:00Z'
  str_pat = '\\'+pat if str==type(pat) else '$|^'.join(['\\'+s for o in pat])
  sql='''SELECT COUNT(ip) AS tot, COUNT(DISTINCT ip) AS uni 
    FROM %s
    WHERE time >= '%s' AND time < '%s' and req_dir =~ /^%s$/
    GROUP BY req_base, cc2''' % (table, dt_start, dt_end, str_pat)
  print sql
  result = influx.query(sql)
  for row in list(result.get_points()) :
    insert2mysql(prod,row)

prod_pattern = {# {{{
  'player'         : [ 'install', 'cancel', 'uninstall', 'playing', 'family', 'font', 'setting', 'update' ],
  'audio'          : [ 'install', 'cancel', 'uninstall', 'playing', 'action', 'playlog', 'synclyriceditor' ],
  'cam'            : [ 'install', 'cancel', 'uninstall' ],
  'gomcam'         : [ 'action', 'play' ],
  'studio'         : [ 'install', 'cancel', 'uninstall', 'playing', 'action' ],
  'mix'            : [ 'install', 'cancel', 'uninstall' ],
  'totalpromotion' : [ 'install', 'cancel', 'view' ]
}# }}}

prod_pattern = {# {{{
  'player' : '/player',
  'audio'  : '/audio',
  'cam'    : [ '/cam', '/gomcam' ],
  'studio' : '/studio',
  'mix'    : '/mix'
}# }}}

if __name__ == "__main__":
  today = date.today()
  today_ymd = today.strftime('%y%m%d')
  filename = os.path.basename(__file__)
  log_file = BIN_PATH + "log/%s.%s"%(filename[:filename.rfind('.')],today_ymd)
  setup_logger('log_batch', log_file )
  log_batch = logging.getLogger('log_batch')

  startday = today - timedelta(days=1)
  if 1 < len(sys.argv) :
    startday = datetime.strptime( sys.argv[1], '%y%m%d' ).date()
  delta = today - startday

  for d in [startday + timedelta(days=x) for x in range(0,delta.days)] :
    d_ymd = d.strftime('%y%m%d')
    setup_logger('log'+d_ymd, log_file+'.'+d_ymd )
    log_daily = logging.getLogger('log'+d_ymd)
    print d_ymd
    log_batch.info( '---=== '+d_ymd+' ===---' )
    for prod in prod_pattern :
      ts_start = datetime.now()
      import_stat ( d, prod, prod_pattern[prod] )
      log = "end: %s\t%s" % (prod, str(datetime.now()-ts_start) )
      print log
      log_batch.info( log )

cursor.close()
cnx.close()
