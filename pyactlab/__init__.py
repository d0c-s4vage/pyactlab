import json
import os
import re
import urllib

import models

try:
    import requests # non-standard, needs to be installed
except ImportError as e:
    print("requests module is missing")
    print("run\n\n\tpip install requests\n\nto resolve this error!\n\n")
    raise

try:
    import xmltodict
except ImportError as e:
    print("xmltodict module is missing")
    print("run\n\n\tpip install xmltodict\n\nto resolve this error!\n\n")
    exit

class ActLabError(Exception): pass
class ConnectionError(ActLabError): pass
class InvalidCredentialsError(ActLabError): pass
class InvalidAttachment(ActLabError): pass

class ActLabClient(object):
    """
    ActiveCollab restful API client. Intended to be used in a git post-receive
    hook to push up changes to or create new notebooks
    """

    _client_name = "ActLabClient"
    _client_vendor = "PYACTLAB"

    # TODO - static method to fetch API key from email/password
    def __init__(self, host, key=None, email=None, password=None, base_path="/"):
        """
        """
        self._host = host
        while self._host.endswith("/"):
            self._host = self._host[:-1]
        if not self._host.startswith("http"):
            self._host = "http://" + self._host

        self._base_path = base_path
        if not self._base_path.endswith("/"):
            self._base_path += "/"
        self._api_path = self._base_path + "api/v1"

        self._key = None
        if key is not None:
            self._key = key
            self._test_key()
        elif email is not None and password is not None:
            self._key = self._get_api_key(email, password)

            if self._key is None:
                raise InvalidCredentialsError()
        else:
            raise ActLabError("A key or email and password must be provided!")

    # ------------------------
    #  PUBLIC INTERFACE
    # ------------------------

    # COMPANIES -------------------------

    def get_companies(self, raw=False):
        res = self._get_api("companies")
        if res is None:
            return []

        if raw:
            return res

        companies = [models.Company.create(self, c) for c in res]
        return companies
    
    def get_company(self, company_id, raw=False):
        res = self._get_cmd("people/{}".format(company_id))

        if raw:
            return res

        return models.Company.create(self, res)

    # USERS -------------------------

    def new_user(self, email, password, company_id, user_type="Member",  permissions=None, raw=False):
        """
        Create a new user. Possible permissions are: can_manage_settings, can_manage_projects, can_manage_finances
        """
        if permissions is None:
            permissions = []

        res = self._post_api("users", post_params={
            "type"          : user_type,
            "company_id"    : company_id,
            "password"      : password,
            "email"         : email,
        })

        if res is None:
            raise ActLabError("Could not create new user")

        if raw:
            return res

        user = models.User.create(self, res["single"])
        return user
    
    def get_users(self, raw=False):
        """
        Fetch all users in company specified by company_id
        """
        res = self._get_api("users")

        if raw:
            return res

        users = [models.User.create(self, u) for u in res]
        return users
    
    def get_user(self, company_id, user_id, raw=False):
        """
        Fetch the user using the company_id and user_id
        """
        res = self._get_cmd("people/{cid}/users/{uid}".format(
            cid=company_id,
            uid=user_id
        ))

        if raw:
            return res

        user = models.User.create(self, res)
        return user
    
    def save_user(self, user):
        """
        Save the user
        """
        raise NotImplemented("save_user has not yet been implemented")

    # PROJECTS -------------------------

    def get_projects(self, raw=False):
        """
        Get a list of all visible projects
        """
        res = self._get_api("projects")
        if res is None:
            return []

        if raw:
            return res

        projects = [models.Project.create(self, p) for p in res]
        return projects
    
    def get_project(self, project_id, raw=False):
        """
        Return a single project by id
        """
        res = self._get_cmd("projects/" + str(project_id))

        if raw:
            return res

        return models.Project.create(self, res)
    
    def save_project(self, project, **extra):
        """
        Save the project
        """
        fields = dict(project.get_fields().items() + extra.items())
        fields = self._memberify_dict(fields, "project")
        fields["submitted"] = "submitted"
        res = self._post_cmd(
            "projects/" + str(project.id) + "/edit",
            **fields
        )
        return res
    
    def complete_project(self, project):
        """
        Mark the project as being completed. Returns raw json (for use by models)
        """
        fields = {"submitted": "submitted"}
        res = self._post_cmd("projects/{pid}/complete".format(pid=project.id), **fields)
        return res
    
    def new_project(self, **params):
        """
        Create a new project with the specified param values

        param options:
            "name":            str,    # (string) - The project name.
            "overview":        str,    # (text) - The project overview.
            "category_id":    int,    # (integer) - The ID of the Project Category.
            "company_id":    int,    # (integer) - The ID of the Client company that you are working for on this project.
            "leader_id":    int,    # (integer) - The ID of the user who is the Project Leader.
            "status":        str,    # (string) - The project status field is available only for the edit-status action. It has two possible values: active and completed.
            "currency_id":    int,    # (integer) - The ID of the currency that was used to set the budget. If nothing is selected, the default currency will be displayed. You can set a default currency in Administrator > General > Currencies.
            "budget":         float,    # (float) - The value of a Project Budget.
            "label_id":        int        # (integer) - The ID of the Project Label.
        """
        project = models.Project(self, params)
        fields = self._memberify_dict(project.get_fields(), "project")
        fields["submitted"] = "submitted"

        res = self._post_cmd(
            "projects/add",
            **fields
        )
        return models.Project.create(self, res)

    # TASKS -------------------------

    def _create_task(self, project_id, json):
        """
        Create a task from returned json data
        """
        t = models.Task.create(self, json)
        t.task_id = json["task_id"]
        t.project_id = project_id
        return t

    def get_tasks(self, project_id, raw=False, inc_completed=False):
        """
        Fetch a list of all tasks in a project
        """

        res = self._get_api("projects/{pid}/tasks".format(pid=project_id))
        if res is None:
            return []

        if raw:
            return res

        tasks = []
        for t in res["tasks"]:
            if 1 == t["is_completed"] and not inc_completed:
                continue
            task = models.Task.create(self, t)
            tasks.append(task)
        return tasks

    def get_task_labels(self, raw=False):
        """
        Fetch a list of task lists
        """
        res = self._get_api("labels/task-labels")
        if res is None:
            return []

        if raw:
            return res

        task_labels = [models.TaskLabel.create(self, t) for t in res]
        return task_labels

    def get_task_lists(self, project_id, raw=False):
        """
        Fetch a list of task lists
        """
        res = self._get_api("projects/{pid}/task-lists".format(pid=project_id))
        if res is None:
            return []

        if raw:
            return res

        task_lists = [models.TaskList.create(self, t) for t in res]
        return task_lists

    def get_task_list(self, project_id, task_list_id, raw=False):
        """Return the specified task list or None if not found
        """
        res = self._get_api("projects/{pid}/task-lists/{tid}".format(
            pid     = project_id,
            tid     = task_list_id
        ))
        if res is None:
            return None

        if raw:
            return res

        task_list = models.TaskList.create(self, res)
        return task_list

    def get_task(self, project_id, task_id, raw=False):
        """
        Return the task in the project denoted by `project_id` and specified by `task_id`
        """
        res = self._get_api("projects/{pid}/tasks/{tid}".format(pid=project_id, tid=task_id))

        if raw:
            return res

        return self._create_task(project_id, res)
    
    def save_task(self, task, **extra):
        """
        Save the existing task
        """
        if task.project_id is None:
            raise ActLabError("task.project_id must be set!")

        fields = dict(task.get_fields().items() + extra.items())
        fields = self._memberify_dict(fields, "task")
        fields["submitted"] = "submitted"
        res = self._post_cmd(
            "projects/{pid}/tasks/{tid}/edit".format(pid=task.project_id, tid=task.task_id),
            **fields
        )
        return res
    
    def complete_task(self, task):
        """
        Mark the task as being completed. Returns raw json (for use by models)
        """
        fields = {"submitted": "submitted"}
        res = self._post_cmd("projects/{pid}/tasks/{tid}/complete".format(pid=task.project_id, tid=task.task_id), **fields)
        return res

    def new_attachment(self, owner_model, filepath=None, data=None, filename=None, mime_type="application/octet-stream"):
        """I believe this _ONLY_ works on tasks, unlike the old version of active collab
        where everything could have an attachment.
        """
        if filepath is None and data is None:
            raise InvalidAttachment("Could not identify file (data or path both don't make sense)")
       
        if filepath is not None:
            if not os.path.exists(filepath):
                raise InvalidAttachment("Path does not exist at '{}'".format(filepath))

            with open(filepath, "rb") as f:
                file_data = f.read()
            filename = os.path.basename(filepath)
        else:
            file_data = data

        uploaded_file = self._upload_file(file_data=file_data, filename=filename)

        res = self._put_api(owner_model.url_path, post_params={
            "attach_uploaded_files": [
                uploaded_file
            ]
        })

        owner_model._create_fields(res["single"])

    def new_task(self, owner_model, name=None, body=None, assignee_id=None, due_on=None, is_important=None, labels=None, **others):
        base_path = owner_model.url_path + "/tasks"

        if is_important is None:
            is_important = 0

        params = {
            "name"          : name,
            "body"          : body,
            "assignee_id"   : assignee_id,
            "due_on"        : due_on,
            "is_important"  : is_important,
            "labels"        : labels,
        }
        params.update(others)

        res = self._post_api(base_path, post_params=params)
        return models.Task.create(self, res["single"])
    
    def new_task_OLD(self, project_id, **params):
        """
        Create a new task in the project denoted by `project_id` with the
        specified param values

        param options:
            "name":                str,    # (string) - The Task name is a required field when creating a Task.
            "body":                str,    # (text) - The Task description.
            "visibility":        int,    # (integer) - Object visibility. 0 is private and 1 is the value of normal visibility.
            "category_id":        int,    # (integer) - Object category.
            "label_id":            int,    # (integer) - Object label.
            "milestone_id":        int,    # (integer) - ID of the parent Milestone.
            "priority":            int,    # (integer) - The priority can have one of five integer values, ranging from -2 (lowest) to 2 (highest). 0 marks normal.
            "assignee_id":        int,    # (integer) - The user assigned and responsible for the Task.
            "other_assignees":    list,    # (array) - The people assigned to the Task.
            # TODO
            "due_on":            str,    # (date) - The task due date.
            "created_by_id":    int,    # (integer) - Use for a known user who already has an account in the system.
            "created_by_name":    str,    # (string) - Use for anonymous user, who don't have an account in the system (can not be used with created_by_id).
            "created_by_email":    str        # (string) - Used for anonymous users.
        """
        task = models.Task(self, params)
        fields = self._memberify_dict(task.get_fields(), "task")
        fields["submitted"] = "submitted"

        res = self._post_cmd(
            "projects/{pid}/tasks/add".format(pid=project_id),
            **fields
        )
        return self._create_task(project_id, res)
    
    # NOTEBOOKS -------------------------

    # NOTE this is done automatically in the Model in the _create_fields method!
    # def _create_attachments(self, project_id, json):
        # pass

    def _create_page(self, project_id, notebook_id, json):
        """
        Create a page from the abbreviated json that is returned from
        in the `subpages` field of a notebook
        """
        if "id" not in json:
            match = re.match(r'^.*path_info=projects%2F[a-zA-Z0-9-]+%2Fnotebooks%2F\d+%2Fpages%2F(\d+)', json["permalink"])
            if match is None:
                match = re.match(r'^.*/projects/.*/notebooks/[0-9]+/pages/([0-9]+)', json["permalink"])
            id = int(match.group(1))
        else:
            id = json["id"]

        json["id"] = id

        page = models.Page.create(self, json, project_id=project_id, notebook_id=notebook_id)

        # don't get the full contents yet! do this as-needed perhaps?
        # page.refresh()

        subpages = []
        for subpage in json["subpages"]:
            page = self._create_page(project_id, subpage)
            page.parent_id = id
            subpages.append(page)

        page.subpages = subpages
        page.project_id = project_id
        page.notebook_id = notebook_id

        return page

    def _create_notebook(self, project_id, json):
        """
        Create a notebook from the given json, also creating subpages and setting
        the root page of the notebook.
        """
        notebook = models.Notebook.create(self, json)
        pages = []
        for p in json["subpages"]:
            pages.append(self._create_page(project_id, notebook.id, p))
        notebook.subpages = pages
        notebook.project_id = project_id

        return notebook

    def get_notebooks(self, project_id, raw=False):
        """
        Fetch a list of all notebooks in a project
        """
        res = self._get_cmd("projects/{pid}/notebooks".format(pid=project_id))
        if res is None:
            return []

        if raw:
            return res

        notebooks = []
        for n in res:
            notebook = self._create_notebook(project_id, n)
            notebook.project_id = project_id
            notebooks.append(notebook)
        return notebooks

    def get_notebook(self, project_id, notebook_id, raw=False):
        """
        Return the notebook in the project denoted by `project_id` and specified by `notebook_id`
        """
        res = self._get_cmd("projects/{pid}/notebooks/{nid}".format(pid=project_id, nid=notebook_id))

        if raw:
            return res

        return self._create_notebook(project_id, res)
    
    def save_notebook(self, notebook, **extra):
        """
        Save the existing notebook
        """
        if notebook.project_id is None:
            raise ActLabError("notebook.project_id must be set!")

        fields = dict(notebook.get_fields().items() + extra.items())
        fields = self._memberify_dict(fields, "notebook")
        fields["submitted"] = "submitted"
        res = self._post_cmd(
            "projects/{pid}/notebooks/{nid}/edit".format(pid=notebook.project_id, nid=notebook.id),
            **fields
        )
        return res
    
    def new_notebook(self, project_id, **params):
        """
        Create a new notebook in the project denoted by `project_id` with the
        specified param values

        param options:
            "name":                str,    # (string) - The Notebook name is a required field when a creating a Notebook.
            "body":                str,    # (text) - The Notebook description.
            "visibility":        int,    # (integer) - Object visibility. 0 marks private visibility and 1 is for normal visibility.
            "milestone_id":        int        # (integer) - The ID of the parent Milestone.
        """
        notebook = models.Notebook(self, params)
        fields = self._memberify_dict(notebook.get_fields(), "notebook")
        fields["submitted"] = "submitted"

        res = self._post_cmd(
            "projects/{pid}/notebooks/add".format(pid=project_id),
            **fields
        )
        return models.Notebook.create(self, res)
        

    # PAGES -------------------------

    def get_notebook_pages(self, project_id, notebook_id, raw=False):
        """
        Get all pages in notebook `notebook_id` in project `project_id`
        """
        raise NotImplemented("Notebook pages are returned along with the notebook!")

        # # NOTE: this url does not exist!
        # res = self._get_cmd("projects/{pid}/notebooks/{nid}/pages".format(pid=project_id, nid=notebook_id))
        # if res is None:
            # return []
        # pages = [models.Page.create(self, p) for p in res]
        # return pages
    
    def get_notebook_page(self, project_id, page_id, notebook_id=0, raw=False):
        """
        Return the notebook in the project denoted by `project_id` and specified by `notebook_id`

        notebook_id IS NOT required to fetch the page, as page_ids are unique within a project,
        not within a notebook.
        """
        res = self._get_cmd("projects/{pid}/notebooks/{nid}/pages/{pageid}".format(
            pid=project_id,
            nid=notebook_id,
            pageid=page_id
        ))

        if raw:
            return res

        page = self._create_page(project_id, res["notebook"]["id"], res)
        page.project_id = project_id
        return page
    
    def save_notebook_page(self, notebook_page, **extra):
        """"
        Save the notebook page
        """
        if notebook_page.project_id is None:
            raise ActLabError("notebook pages must have a project_id in order to save them")
        if notebook_page.notebook_id is None:
            raise ActLabError("notebook pages must have a notebook_id in order to save them")

        fields = dict(notebook_page.get_fields().items() + extra.items())
        fields = self._memberify_dict(fields, "notebook_page")
        fields["submitted"] = "submitted"
        res = self._post_cmd(
            "projects/{pid}/notebooks/{nid}/pages/{pageid}/edit".format(
                pid=notebook_page.project_id,
                nid=notebook_page.notebook_id,
                pageid=notebook_page.id
            ),
            **fields
        )
        return res
    
    def new_notebook_page(self, project_id, notebook_id, **params):
        """
        Create a new notebook page

        param options:
            "name":            None,    # (string) - The Notebook Page title is a required value.
            "body":            None,    # (text) - The Notebook Page description.
            "parent_id":    None    # (integer) - The ID of the parent Page. Leave blank to add the page at the 
        """
        page = models.Page(self, params)
        fields = self._memberify_dict(page.get_fields(), "notebook_page")
        fields["submitted"] = "submitted"

        res = self._post_cmd(
            "projects/{pid}/notebooks/{nid}/pages/add".format(
                pid=project_id,
                nid=notebook_id
            ),
            **fields
        )
        return models.Page.create(self, res)
    
    # MISC -------------------------

    def download_attachment(self, url):
        """
        Download the attachment specified by the url
        """
        dl_url = url + "&auth_api_token=" + self._key
        res = requests.get(dl_url)
        if res.ok:
            return res.content
        else:
            raise ActLabError("Could not download attachment at {}".format(url))
    
    def add_attachment(self, model, name, data, **extra):
        """
        Add an attachment to the model.
        """
        model.save(**{"attachments": {"attachment_0": (name, data)}})
    
    def add_file(self, project, name, data, **extra):
        """
        Add a file to the project
        """
        cmd = self._get_model_url(project) + "/files/files/upload"

        fields = {
            "file[name]": name,
            "file[body]": name,
            "submitted": "submitted",
            "attachments": {
                "attachment_0": (name, data)
            }
        }
        res = self._post_cmd(cmd, **fields)

        return models.File.create(self, res)
    
    def download_file(self, file_obj):
        """
        Download the file, given a file model
        """
        raise NotImplementedError("File downloading is not yet implemented")
        #cmd = self._get_model_url(file_obj.project_id) + "/files/" + file_obj.id
    
    def _create_comment(self, json):
        """
        Create a comment from json
        """
        res = models.Comment.create(self, json)
        res.creator = json["created_by"]["name"]
        res.created_on = json["created_on"]["formatted"]
    
    def get_comments(self, model, raw=False):
        """
        Return a list of comments attached to the model
        """
        cmd = self._get_model_url(model) + "/comments"

        res = self._get_cmd(cmd)
        if res is None:
            return []

        if raw:
            return res

        comments = []
        for c in res:
            comments.append(models.Comment.create(self, c))

        return comments
    
    def add_comment(self, model, msg, raw=False):
        """
        Add a comment to the model
        """
        cmd = self._get_model_url(model) + "/comments/add"
        fields = {
            "comment[body]": msg,
            "submitted": "submitted"
        }

        res = self._post_cmd(cmd, **fields)

        if raw:
            return res

        return models.Comment.create(self, res)

    # ---------------------
    # ---------------------

    def get_key(self):
        """
        Return the api key
        """
        return self._key

    # ------------------------
    #  UTILITY
    # ------------------------

    def _upload_file(self, file_data, filename):
        """Upload the file and return the returned file info

        :file_name: The name of the file
        :file_data: The file data
        :returns: a dict of file info
        """
        fields = {
            "file[name]": filename,
            "file[body]": file_data,
            "submitted": "submitted",
            "attachments": {
                "attachment_0": (filename, file_data, "application/octet-stream"),
            },
        }
        res = self._post_api("upload-files", post_params=fields)
        return res[0]["code"]

    def _get_model_url_OLD(self, model):
        """
        Return the url of the model to be used in path_info
        """
        cmd = ""
        if hasattr(model, "project_id"):
            cmd += "projects/{pid}/".format(pid=model.project_id)
        cmd += model.method + "s/" + str(getattr(model, model.id_field))

        return cmd

    def _memberify_dict(self, d, body_name, excludeNone=True):
        """
        Memberify key values in a dictionary with the body_name.

        E.g: { "name": "Project name" } --> { "project[name]": "Project name" }
        """
        res = {}
        for k,v in d.iteritems():
            if v is None and excludeNone:
                continue
            if k == "attachments":
                res[k] = v
            else:
                res["{p}[{k}]".format(p=body_name, k=k)] = v
        return res

    def _debug(self, msg):
        """
        Placeholder until I feel like doing real logging :^/
        """
        print(msg)

    def _esc(self, string, safe="/"):
        """
        url-escape the provided `string`, using `safe` chars as "safe" characters that
        are not to be url-escaped. `safe` defaults to ""
        """
        return urllib.quote(string, safe)
    
    def _dict_to_query(self, d):
        """
        convert a dictionary to a query-string, url-escaping the values
        """
        return "&".join("{k}={v}".format(k=k, v=self._esc(v)) for k,v in d.iteritems())
    
    def _auto_convert(self, data):
        try:
            return json.loads(data)
        except:
            try:
                return xmltodict.parse(data)
            except:
                return data

    # ------------------------
    #  PRIVATE CORE
    # ------------------------

    def _api_url(self, page, **params):
        """
        Build an api url using `self._host`, `self._api_path`, and provided args
        """
        while page.startswith("/"):
            page = page[1:]
        while page.endswith("/"):
            page = page[:-1]
            
        url = self._host + self._api_path + "/" + page
        if len(params) > 0:
            params_str = self._dict_to_query(params)
            url += "?" + params_str
        return url
    
    def _api_url_OLD(self, **params):
        """
        Build an api url using `self._host`, `self._api_path`, and provided args
        """
        url = self._host + self._api_path
        if len(params) > 0:
            params_str = self._dict_to_query(params)
            url += "?" + params_str
        return url

    def _get_api(self, page, query_params=None):
        """
        Normal arguments are path parts, kwargs are the GET param key/value pairs
        """
        if query_params is None: query_params = {}

        url = self._api_url(page, **query_params)

        headers = {}
        if self._key is not None:
            headers["X-Angie-AuthApiToken"] = self._key

        try:
            res = requests.get(url, headers=headers, verify=False)
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError()

        if res.ok:
            return self._auto_convert(res.content)
        else:
            return None
    
    def _get_api_OLD(self, query_params=None):
        """
        Normal arguments are path parts, kwargs are the GET param key/value pairs
        """
        if query_params is None: query_params = {}

        url = self._api_url(**query_params)

        try:
            res = requests.get(url)
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError()

        if res.ok:
            return self._auto_convert(res.content)
        else:
            return None

    def _put_api(self, page, query_params=None, post_params=None):
        if query_params is None: query_params = {}
        if post_params is None: post_params = {}

        url = self._api_url(page, **query_params)

        files = []
        if "attachments" in post_params:
            files = post_params["attachments"]
            del post_params["attachments"]

        headers = {}
        if self._key is not None:
            headers["X-Angie-AuthApiToken"] = self._key

        try:
            if len(files) == 0:
                post_params = json.dumps(post_params)
                headers["Content-Type"] = "application/json"

            res = requests.put(url, data=post_params, headers=headers, files=files, verify=False)
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError()

        if res.ok:
            return self._auto_convert(res.content)
        else:
            return None
        
    def _post_api(self, page, query_params=None, post_params=None):
        if query_params is None: query_params = {}
        if post_params is None: post_params = {}

        url = self._api_url(page, **query_params)

        files = []
        if "attachments" in post_params:
            files = post_params["attachments"]
            del post_params["attachments"]

        headers = {}
        if self._key is not None:
            headers["X-Angie-AuthApiToken"] = self._key

        try:
            if len(files) == 0:
                post_params = json.dumps(post_params)
                headers["Content-Type"] = "application/json"

            res = requests.post(url, data=post_params, headers=headers, files=files, verify=False)
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError()

        if res.ok:
            return self._auto_convert(res.content)
        else:
            return None
    
    def _post_api_OLD(self, query_params=None, post_params=None):
        """
        Normal arguments are path parts, kwargs are the POST param key/value pairs
        """
        if query_params is None: query_params = {}
        if post_params is None: post_params = {}

        files = {}
        if "attachments" in post_params:
            files = post_params["attachments"]
            del post_params["attachments"]

        url = self._api_url(**query_params)

        try:
            res = requests.post(url, post_params, files=files)
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError()

        if res.ok:
            return self._auto_convert(res.content)
        else:
            return None
    
    def _make_cmd_params(self, cmd):
        return {
            "path_info": cmd,
            "auth_api_token": self._key,
            "format": "json"
        }
    
    def _post_cmd(self, cmd, **params):
        return self._post_api(self._make_cmd_params(cmd), params)
    
    def _get_cmd(self, cmd, **params):
        url_params = self._make_cmd_params(cmd)
        url_params = dict(url_params.items() + params.items())
        return self._get_api(url_params)

    def _test_key(self):
        """
        Test the validity of the api key by fetching a list of companies
        """
        # let any errors bubble up
        self.get_companies(raw=True)
    
    def _get_api_key(self, email, password):
        """Fetch the api key for this email/password combination

        :email: TODO
        :password: TODO
        :returns: TODO

        """
        res = self._post_api("issue-token", post_params={
            "username": email,
            "password": password,
            "client_name": self._client_name,
            "client_vendor": self._client_vendor,
        })
        if res is None:
            raise InvalidCredentialsError

        return res["token"]

    def _get_api_key_OLD(self, email, password):
        """
        Fetch the api key using the provided `email` and `password`.

        https://activecollab.com/help/books/api/authentication.html
        """ 
        res = self._post_api(post_params={
            "api_subscription[email]": email,
            "api_subscription[password]": password,
            "api_subscription[client_name]": self._client_name,
            "api_subscription[client_vendor]": self._client_vendor
        })
        if res is None:
            # log it
            self._debug("Could not fetch api key!")
            return None

        match = re.match(r'^API key:\s*(.*)$', res)
        if match:
            return match.group(1)
        else:
            self._debug("Could not extract API key from " + json.dumps(res))
            return None
