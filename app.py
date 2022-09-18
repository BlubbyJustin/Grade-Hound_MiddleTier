import collections
import datetime
from importlib.machinery import FrozenImporter
import json
import logging
import os
from typing import Dict

from flask import Flask, render_template, request, Response

import sqlalchemy

from connect_connector import connect_with_connector

app = Flask(__name__)


def init_connection_pool() -> sqlalchemy.engine.base.Engine:

    if os.environ.get("INSTANCE_CONNECTION_NAME"):
        return connect_with_connector()

    raise ValueError(
        "Missing database connection type. Please define one of INSTANCE_HOST, INSTANCE_UNIX_SOCKET, or INSTANCE_CONNECTION_NAME"
    )

db = None

@app.before_first_request
def init_db() -> sqlalchemy.engine.base.Engine:
    global db
    db = init_connection_pool()


@app.route("/")
def hello():
    """Return a friendly HTTP greeting."""
    message = "It's running!"

    """Get Cloud Run environment variables."""
    service = os.environ.get('K_SERVICE', 'Unknown service')
    revision = os.environ.get('K_REVISION', 'Unknown revision')

    return render_template('index.html',
        message=message,
        Service=service,
        Revision=revision)

@app.route("/addUser", methods = ['POST'])
def addUser():
    if(request.method == 'POST'):
        request_data = json.loads(request.data.decode('utf-8'))
        userId = request_data['userId']
        firstName = request_data['firstName']
        lastName = request_data['lastName']
        with db.connect() as conn:
            conn.execute(f"INSERT INTO users(user_id, first_name, last_name)Values('{userId}', '{firstName}', '{lastName}');")
        with db.connect() as conn:
            conn.execute("COMMIT")
    return ''

@app.route('/getFirstName', methods = ['GET', 'POST'])
def getFirstName():
    global formatedData
    if(request.method == 'POST'):
        request_data = json.loads(request.data.decode('utf-8'))
        userId = request_data['userId']
        with db.connect() as conn:
            cursor = conn.execute(f"SELECT first_name FROM users WHERE user_id = '{userId}';")
        data = cursor.fetchall()
        firstName = data[0][0]
    return {'firstName':firstName}

def averageAList(numberList):
    sum = 0
    for number in numberList:
        sum += number
    if(len(numberList) != 0):
        return sum/len(numberList)

@app.route('/fetchClassData', methods = ['GET', 'POST'])
def fetchClassData():
    global formatedData
    if(request.method == 'POST'):
        request_data = json.loads(request.data.decode('utf-8'))
        userId = request_data['userId']
        with db.connect() as conn:
            cursor = conn.execute(f"SELECT * FROM classes WHERE user_id = '{userId}' ORDER BY class_id;")
        classData = cursor.fetchall()
        classesList = []
        for row in classData:
            d = collections.OrderedDict()
            d['classId'] = row[0]
            d['userId'] = row[1]
            d['className'] = row[2]
            d['targetGrade'] = row[3]
            d['currentGrade'] = '{:.2f}'.format(row[4])
            d['level'] = row[5]
            classesList.append(d)
        formatedData = json.dumps(classesList)
        if(len(formatedData) == 0):
            formatedData = {'status': 'no classes'}
        return ''
    else:
        return formatedData

@app.route('/addClass', methods = ['POST'])
def addClass():
    if(request.method == 'POST'):
        request_data = json.loads(request.data.decode('utf-8'))
        userId = request_data['userId']
        className = request_data['className']
        targetGrade = request_data['targetGrade']
        with db.connect() as conn:
            conn.execute(f"INSERT INTO classes(user_id, name, target_grade, current_grade, level)Values('{userId}', '{className}', {targetGrade}, 0, 'CP1');")
        with db.connect() as conn:
            conn.execute("COMMIT")
    with db.connect() as conn:
        cursor = conn.execute(f"SELECT class_id FROM classes WHERE user_id = '{userId}' AND name = '{className}';")
    classData = cursor.fetchall()
    classId = classData[0][0]
    with db.connect() as conn:
        conn.execute(f"INSERT INTO types(class_id, type_name, weight)Values({classId}, 'Test', 50), ({classId}, 'Quiz', 40), ({classId}, 'Homework', 10);")
    with db.connect() as conn:
        conn.execute("COMMIT")
    return {'classId': classId}

@app.route('/deleteClass', methods = ['POST'])
def deleteClass():
    if(request.method == 'POST'):
        request_data = json.loads(request.data.decode('utf-8'))
        userId = request_data['userId']
        classId = request_data['classId']
        with db.connect() as conn:
            conn.execute(f"DELETE FROM types WHERE class_id = {classId};")
        with db.connect() as conn:
            conn.execute("COMMIT")
        with db.connect() as conn:
            conn.execute(f"DELETE FROM assignments WHERE class_id = {classId};")
        with db.connect() as conn:
            conn.execute("COMMIT")
        with db.connect() as conn:
            conn.execute(f"DELETE FROM classes WHERE class_id = {classId};")
        with db.connect() as conn:
            conn.execute("COMMIT")
    return ''

@app.route('/deleteUser', methods = ['POST'])
def deleteUser():
    if(request.method == 'POST'):
        request_data = json.loads(request.data.decode('utf-8'))
        userId = request_data['userId']
        with db.connect() as conn:
            cursor = conn.execute(f"SELECT class_id FROM classes WHERE user_id = '{userId}';")
        classData = cursor.fetchall()
        if(len(classData) == 0):
            with db.connect() as conn:
                conn.execute(f"DELETE FROM users WHERE user_id = '{userId}';")
        else: #this no work what the fuck
            for cid in classData:
                with db.connect() as conn:
                    conn.execute(f"DELETE FROM types WHERE class_id = {cid[0]};")
                with db.connect() as conn:
                    conn.execute("COMMIT")
                with db.connect() as conn:
                    conn.execute(f"DELETE FROM assignments WHERE class_id = {cid[0]};")
                with db.connect() as conn:
                    conn.execute("COMMIT")
                with db.connect() as conn:
                    conn.execute(f"DELETE FROM classes WHERE class_id = {cid[0]};")
                with db.connect() as conn:
                    conn.execute("COMMIT")
            with db.connect() as conn:
                conn.execute(f"DELETE FROM users WHERE user_id = '{userId}';")
            with db.connect() as conn:
                    conn.execute("COMMIT")
    return ''

@app.route('/fetchAssignmentData', methods = ['GET', 'POST'])
def fetchAssignmentData(): #//LMAO LETS START IT
    global formatedData
    if(request.method == 'POST'):
        request_data = json.loads(request.data.decode('utf-8'))
        classId = request_data['classId']
        with db.connect() as conn:
            cursor = conn.execute(f"SELECT * FROM assignments WHERE class_id = {classId};")
        assignmentData = cursor.fetchall()
        assignmentList = []
        for row in assignmentData:
            d = collections.OrderedDict()
            d['assignmentId'] = row[0]
            d['classId'] = row[1]
            d['type'] = row[2]
            d['name'] = row[3]
            d['grade'] = row[4]
            d['date'] = str(row[5])
            d['comment'] = row[6]
            assignmentList.append(d)
        formatedData = json.dumps(assignmentList)
        return ''
    else:
        return formatedData

@app.route('/addAssignment', methods = ['POST'])
def addAssignment():
    if(request.method == 'POST'):
        request_data = json.loads(request.data.decode('utf-8'))
        classId = request_data['classId']
        type = request_data['type']
        name = request_data['name']
        grade = request_data['grade']
        date = request_data['date']
        comment = request_data['comment']
        with db.connect() as conn:
            conn.execute(f"INSERT INTO assignments(class_id, type, name, grade, date, comment)Values({classId}, '{type}', '{name}', {grade}, '{date}', '{comment}');")
        with db.connect() as conn:
            conn.execute("COMMIT")
    return ''

@app.route('/deleteAssignment', methods = ['POST'])
def deleteAssignment():
    if(request.method == 'POST'):
        request_data = json.loads(request.data.decode('utf-8'))
        assignmentId = request_data['assignmentId']
        with db.connect() as conn:
            conn.execute(f"DELETE FROM assignments WHERE assignment_id = {assignmentId};")
        with db.connect() as conn:
            conn.execute("COMMIT")
    return ''

@app.route('/editAssignmentComment', methods = ['POST'])
def editAssignmentComment():
    if(request.method == 'POST'):
        request_data = json.loads(request.data.decode('utf-8'))
        assignmentId = request_data['assignmentId']
        comment = request_data['comment']
        with db.connect() as conn:
            conn.execute(f"UPDATE assignments SET comment = '{comment}' WHERE assignment_id = {assignmentId};")
        with db.connect() as conn:
            conn.execute("COMMIT")
    return ''


@app.route('/recalcAverage', methods = ['POST'])
def recalcAverage():

    newAverage = 0
    if(request.method == 'POST'):

        request_data = json.loads(request.data.decode('utf-8'))
        classId = request_data['classId']

        with db.connect() as conn:
            cursor = conn.execute(f"SELECT grade, type FROM assignments WHERE class_id = {classId};")
        assignmentData = cursor.fetchall()
        assignmentList = []
        for row in assignmentData:
            d = collections.OrderedDict()
            d['grade'] = row[0]
            d['type'] = row[1]
            assignmentList.append(d)
        formattedAssignments = json.dumps(assignmentList)
        assignments = json.loads(formattedAssignments)

        with db.connect() as conn:
            cursor = conn.execute(f"SELECT type_name, weight FROM types WHERE class_id = {classId} ORDER BY type_id;")
        typesData = cursor.fetchall()
        typesList = []
        for row in typesData:
            d = collections.OrderedDict()
            d['typeName'] = row[0]
            d['weight'] = row[1]
            typesList.append(d)
        formattedTypes = json.dumps(typesList)
        types = json.loads(formattedTypes)

        newAverage = 0

        typesNotInputtedList = []
        for type in types:
            #check if there are any types with no assignment inputs yet (need to adjust calc algorithm)
            gradeList = []
            for assignment in assignments:
                if (assignment['type'] == type['typeName']):
                    gradeList.append(assignment['grade'])
            if (len(gradeList) == 0):
                typesNotInputtedList.append([type['weight'], type['typeName']])
        
        if(len(typesNotInputtedList) == 0): # if all the types HAVE assignmnts inputted
            for type in types:
                gradeList = []
                for assignment in assignments:
                    if (assignment['type'] == type['typeName']):
                        gradeList.append(assignment['grade'])
                average = averageAList(gradeList)
                newAverage += average * (type['weight']/100)
        else: #if some of the types have assignments inputted

            #get list of just type names that have no inputs
            noInputTypeName = []
            for type in typesNotInputtedList:
                noInputTypeName.append(type[1])

            typesNotFilledPercentage = 0
            for unfilledType in typesNotInputtedList:
                typesNotFilledPercentage += unfilledType[0] #index 0 would be weight
            
            percentageLeft = 100 - typesNotFilledPercentage
            for type in types:
                gradeList = []
                for assignment in assignments:
                    validTypes = True #boolean shows if a type with no input is being checked against
                    if type['typeName'] in noInputTypeName:
                        validTypes = False
                    if ((assignment['type'] == type['typeName']) and validTypes == True):
                        gradeList.append(assignment['grade'])
                if(len(gradeList) != 0): #This is a cheat, for some reason the valid value check doesnt work? Or something
                    average = averageAList(gradeList)
                    newAverage += (average * (type['weight']/100)) / (percentageLeft/100)

        with db.connect() as conn:
            conn.execute(f"UPDATE classes SET current_grade = {newAverage} WHERE class_id = {classId};")
        with db.connect() as conn:
            conn.execute("COMMIT")

    return {'newAverage': '{:.2f}'.format(newAverage)}

@app.route('/initTypesList', methods = ['GET', 'POST'])
def initTypesList(): #//LMAO LETS START IT
    global formatedData
    if(request.method == 'POST'):
        request_data = json.loads(request.data.decode('utf-8'))
        classId = request_data['classId']
        with db.connect() as conn:
            cursor = conn.execute(f"SELECT type_name, weight FROM types WHERE class_id = {classId} ORDER BY type_id;")
        typesData = cursor.fetchall()
        typesList = []
        for row in typesData:
            d = collections.OrderedDict()
            d['typeName'] = row[0]
            d['weight'] = row[1]
            typesList.append(d)
        formatedData = json.dumps(typesList)
        return ''
    else:
        return formatedData

@app.route('/addType', methods = ['GET', 'POST'])
def addType(): 
    global formatedData
    if(request.method == 'POST'):
        request_data = json.loads(request.data.decode('utf-8'))
        classId = request_data['classId']
        typeName = request_data['typeName']
        weight = request_data['weight']
        with db.connect() as conn:
            cursor = conn.execute(f"INSERT INTO types(class_id, type_name, weight) VALUES({classId}, '{typeName}', {weight});")
        with db.connect() as conn:
            cursor = conn.execute("COMMIT;")
        with db.connect() as conn:
            cursor = conn.execute(f"SELECT type_name, weight FROM types WHERE class_id = {classId} ORDER BY type_id;")
        typesData = cursor.fetchall()
        typesList = []
        for row in typesData:
            d = collections.OrderedDict()
            d['typeName'] = row[0]
            d['weight'] = row[1]
            typesList.append(d)
        formatedData = json.dumps(typesList)
        return ''
    else:
        return formatedData

@app.route('/changeTypeName', methods = ['GET', 'POST'])
def changeTypeName(): 
    global formatedData
    if(request.method == 'POST'):
        request_data = json.loads(request.data.decode('utf-8'))
        classId = request_data['classId']
        newName = request_data['newName']
        oldName = request_data['oldName']
        with db.connect() as conn:
            cursor = conn.execute(f"UPDATE types SET type_name = '{newName}' WHERE class_id = {classId} AND type_name = '{oldName}';")
        with db.connect() as conn:
            cursor = conn.execute("COMMIT;")
        with db.connect() as conn:
            cursor = conn.execute(f"SELECT type_name, weight FROM types WHERE class_id = {classId} ORDER BY type_id;")
        typesData = cursor.fetchall()
        typesList = []
        for row in typesData:
            d = collections.OrderedDict()
            d['typeName'] = row[0]
            d['weight'] = row[1]
            typesList.append(d)
        formatedData = json.dumps(typesList)

        #update all assignments with old type name to new one
        with db.connect() as conn:
            cursor = conn.execute(f"UPDATE assignments SET type = '{newName}' WHERE class_id = {classId} AND type = '{oldName}';")
        with db.connect() as conn:
            cursor = conn.execute("COMMIT;")

        return ''
    else:
        return formatedData

@app.route('/changeTypeWeight', methods = ['POST'])
def changeTypeWeight(): 
    global formatedData
    if(request.method == 'POST'):
        request_data = json.loads(request.data.decode('utf-8'))
        classId = request_data['classId']
        typeName = request_data['typeName']
        weight = request_data['weight']
        with db.connect() as conn:
            conn.execute(f"UPDATE types SET weight = {weight} WHERE class_id = {classId} AND type_name = '{typeName}';")
        with db.connect() as conn:
            conn.execute("COMMIT;")

        return ''

@app.route('/deleteType', methods = ['GET', 'POST'])
def deleteType(): 
    global formatedData
    if(request.method == 'POST'):
        request_data = json.loads(request.data.decode('utf-8'))
        classId = request_data['classId']
        typeName = request_data['typeName']
        weight = request_data['weight']
        typeNameRecievingWeight = request_data['typeNameRecievingWeight']
        typeWeightRecievingWeight = request_data['typeWeightRecievingWeight']

        with db.connect() as conn:
            cursor = conn.execute(f"DELETE FROM types WHERE class_id = {classId} AND type_name = '{typeName}' AND weight = {weight};")
        with db.connect() as conn:
            cursor = conn.execute("COMMIT;")

        with db.connect() as conn: 
            cursor = conn.execute(f"UPDATE types SET weight = {typeWeightRecievingWeight + weight} WHERE class_id = {classId} AND type_name = '{typeNameRecievingWeight}';")
        with db.connect() as conn:
            cursor = conn.execute("COMMIT;")
        
        with db.connect() as conn:
            cursor = conn.execute(f"SELECT type_name, weight FROM types WHERE class_id = {classId} ORDER BY type_id;")
        typesData = cursor.fetchall()
        typesList = []
        for row in typesData:
            d = collections.OrderedDict()
            d['typeName'] = row[0]
            d['weight'] = row[1]
            typesList.append(d)
        formatedData = json.dumps(typesList)
        with db.connect() as conn: 
            cursor = conn.execute(f"DELETE FROM assignments WHERE type = '{typeName}' AND class_id = {classId};")
        with db.connect() as conn:
            cursor = conn.execute("COMMIT;")
        return ''
    else:
        return formatedData

@app.route('/filterAssignmentList', methods = ['GET', 'POST'])
def filterAssignmentList(): #//LMAO LETS START IT
    global formatedData
    if(request.method == 'POST'):
        request_data = json.loads(request.data.decode('utf-8'))
        classId = request_data['classId']
        types = request_data['types']
        startDate = request_data['startDate']
        endDate = request_data['endDate']
        minGrade = request_data['minGrade']
        maxGrade = request_data['maxGrade']
        with db.connect() as conn:
            cursor = conn.execute(f"SELECT * FROM assignments WHERE class_id = {classId} AND date >= '{startDate}' AND date <= '{endDate}' AND grade >= {minGrade} AND grade <= {maxGrade};")
        assignmentData = cursor.fetchall()
        assignmentList = []
        for row in assignmentData:
            if(row[2] in types):
                d = collections.OrderedDict()
                d['assignmentId'] = row[0]
                d['classId'] = row[1]
                d['type'] = row[2]
                d['name'] = row[3]
                d['grade'] = row[4]
                d['date'] = str(row[5])
                d['comment'] = row[6]
                assignmentList.append(d)
        formatedData = json.dumps(assignmentList)
        return ''
    else:
        return formatedData

@app.route('/changeClassLevel', methods = ['POST'])
def changeClassLevel():
    if(request.method == 'POST'):
        request_data = json.loads(request.data.decode('utf-8'))
        classId = request_data['classId']
        newClassLevel = request_data['newClassLevel']
        with db.connect() as conn:
            conn.execute(f"UPDATE classes SET level = '{newClassLevel}' WHERE class_id = {classId};")
        with db.connect() as conn:
            conn.execute("COMMIT")
    return ''

@app.route('/initClassLevel', methods = ['GET', 'POST'])
def initClassLevel(): 
    global formatedData
    if(request.method == 'POST'):
        request_data = json.loads(request.data.decode('utf-8'))
        classId = request_data['classId']
        with db.connect() as conn:
            cursor = conn.execute(f"SELECT level FROM classes WHERE class_id = {classId};")
        data = cursor.fetchall()
        list = []
        for row in data:
            d = collections.OrderedDict()
            d['level'] = row[0]
            list.append(d)
        formatedData = json.dumps(list)
        return ''
    else:
        return formatedData

if __name__ == '__main__':
    server_port = os.environ.get('PORT', '8080')
    app.run(debug=True, port=server_port, host='0.0.0.0')



    