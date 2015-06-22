import json

class Model(object):
	"""
	Base class for all PyActLab models
	"""

	# ---------------------------------
	# STATIC
	# ---------------------------------

	@classmethod
	def create(cls, client, fields, **kwargs):
		"""
		Create a new Model with the field key/value pairs
		"""
		res = cls(client, fields, **kwargs)
		return res
	
	# ---------------------------------
	# PUBLIC
	# ---------------------------------

	method = None
	id_field = "id"

	fields = {}
	__fields = None
	__field_types = None
	sub_models = {}
	needs_project_id = True
	attachments = []
	accept_all_fields = False

	creator =		None # id of the creator
	created_on =	None # formatted date/time

	def __init__(self, client, fields=None, **extra):
		"""
		Create a new model
		"""
		self._client = client

		# for project_id, notebook_id, etc
		for k,v in extra.iteritems():
			if hasattr(self, k):
				setattr(self, k, v)

		self._create_fields(init=fields)
	
	def get_fields(self):
		"""
		Return a copy of this model's fields dict
		"""
		return self.__fields.copy()
	
	def save(self, **with_extra):
		"""
		Save the model to active collab. Return false if the model could not be saved
		"""
		if self.id:
			new_fields = getattr(self._client, "save_" + self.method)(self, **with_extra)
			self._create_fields(new_fields)
			return True
		return False
	
	def refresh(self):
		"""
		Refresh the model with what is currently found in active collab
		"""
		if self.id is None:
			print("({cls}): self.id is None, can't refresh".format(cls=self.__class__.__name__))
			return

		if self.needs_project_id and self.project_id is None:
			print("({cls}): self.project_id is None, can't refresh".format(cls=self.__class__.__name__))
			return

		if self.needs_project_id:
			args = [self.project_id, self.id]
		else:
			args = [self.id]

		res = getattr(self._client, "get_" + self.method)(*args, raw=True)
		self._create_fields(res)

	def complete(self):
		"""
		Complete the model (project/task-specific)
		"""
		res = getattr(self._client, "complete_" + self.method)(self)
		self._create_fields(res)
	
	def comment(self, msg):
		"""
		Comment on the current model
		"""
		self._client.add_comment(self, msg)
	
	def get_comments(self):
		"""
		Return a list of comments attached to this model
		"""
		return self._client.get_comments(self)
	
	def attach(self, filename, file_contents, **extra):
		"""
		Add an attachment to the model
		"""
		self._client.add_attachment(self, filename, file_contents, **extra)
	
	# ---------------------------------
	# PRIVATE
	# ---------------------------------

	def _get_class(self, item):
		"""
		Return the class of the item. If the item is a class already,
		return the item
		"""
		# it's already a class, return it
		if type(item) == type:
			return item

		# get the class
		return item.__class__

	def _add_std_fields(self, json):
		"""
		Add standard fields to the model such as creator, created_on, etc
		"""
		if "created_by" in json and json["created_by"] is not None:
			self.creator = json["created_by"]["name"]

		if "created_on" in json and json["created_on"] is not None:
			created_field = json["created_on"]
			if isinstance(created_field, dict):
				self.created_on = created_field["formatted"]
			elif isinstance(created_field, basestring):
				self.created_on = created_field

	def _create_fields(self, init=None):
		"""
		Instantiate (or make copies of the defaults) of each field defined
		in this model's fields dict, casting values where appropriate
		"""
		# don't require the user to define this, hardcode it in
		if "id" not in self.fields:
			self.fields["id"] = int

		if self.__fields is None:
			self.__fields = {}
		if self.__field_types is None:
			self.__field_types = self.fields.copy()

		for k,v in self.fields.iteritems():
			if type(v) is type:
				# do NOT instantiate this at this moment, leave the values
				# as None
				v = None
			else:
				self.__field_types[k] = v.__class__

			if init is not None and k in init:
				cls = self._get_class(self.__field_types[k])

				# make sure it's the appropriate type
				# also don't try to cast it to something if it is None
				if init[k] is not None:
					if cls is unicode:
						v = cls(init[k]).encode("utf-8")
					else:
						v = cls(init[k])
				else:
					v = None

                        if k in self.__fields and self.__fields[k] is not None and v is None:
                            continue

			self.__fields[k] = v

		# add any non-defined fields to self.__fields
		if init and self.accept_all_fields:
			for k,v in init.iteritems():
				if k not in self.__fields:
					self.__fields[k] = v

		if init is not None and "attachments" in init:
			self._create_attachments(init["attachments"])

		if init:
			self._add_std_fields(init)

	def _create_attachments(self, json):
		self.attachments = []
		for a in json:
			attachment = Attachment.create(self._client, a)
			self.attachments.append(attachment)
	
	def __getitem__(self, k):
		"""
		Allow key-based item accessing
		"""
		return getattr(self, k)
	
	def __setitem__(self, k, v):
		"""
		Allow key-based item setting
		"""
		return setattr(self, k, v)

	def __getattr__(self, k):
		"""
		Allow users to access model members directly via dot notation
		"""
		if self.__fields is not None and k in self.__fields:
			return self.__fields[k]
		else:
			return object.__getattribute__(self, k)

	def __setattr__(self, k, v):
		"""
		Allow users to set model members directly via dot notation
		"""
		if self.__fields is not None and k in self.__fields:
			self.__fields[k] = v
			return v
		else:
			return object.__setattr__(self, k, v)


# ---------------------------------
# MODEL DEFINITIONS
# ---------------------------------

class User(Model):
	method = "user"
	needs_project_id = False
	fields = {
		"email":			unicode,	# (string) - The user's email address. The value of this field is required when a User Account is created and must be properly formatted. There can be only one user associated with any given email address in the system.
		#"password":			unicode,	# (string) - The user's password. A value for this field is required when a User Account is created. Minimal length of the password is 3 characters.
		#"password_a":		unicode,	# (string) - The user's password repeated. A value for this field is required when a User Account is created
		"first_name":		unicode,	# (string) - The name of the user
		"last_name":		unicode,	# (string) - The last name of that user
		"type":				unicode,	# (string) - Name of the System Role that this user is having. Five values are possible: Administrator, Manager, Member, Subcontractor and Client. Extra permissions can be set by using custom_permissions property
		"title":			unicode,	# (string) - The user's title
		"phone_mobile":		unicode,	# (string) - The user's mobile phone contact information
		"phone_work":		unicode		# (string) - The user's work phone contact information
	}

class Company(Model):
	method = "people"
	needs_project_id = False
	fields = {
		"name":				unicode,	# (string) - company name. Value of this field is required and needs to be unique in the system,
		"office_address":	unicode,	# (string) - address of company headquarter,
		"office_phone":		unicode,	# (string) - office phone number,
		"office_fax":		unicode,	# (string) - office fax number,
		"office_homepage":	unicode,	# (string) - official company website,
		"note":				unicode		# (string) - company note, if there is any.
	}
	sub_models = {
		"users": "User"
	}

class Project(Model):
	method = "project"
	needs_project_id = False
	fields = {
		"name":			unicode,	# (string) - The project name.
		"overview":		unicode,	# (text) - The project overview.
		"category_id":	int,	# (integer) - The ID of the Project Category.
		"company_id":	int,	# (integer) - The ID of the Client company that you are working for on this project.
		"leader_id":	int,	# (integer) - The ID of the user who is the Project Leader.
		"status":		unicode,	# (string) - The project status field is available only for the edit-status action. It has two possible values: active and completed.
		"currency_id":	int,	# (integer) - The ID of the currency that was used to set the budget. If nothing is selected, the default currency will be displayed. You can set a default currency in Administrator > General > Currencies.
		"budget": 		float,	# (float) - The value of a Project Budget.
		"label_id":		int		# (integer) - The ID of the Project Label.
	}

class Notebook(Model):
	method = "notebook"
	fields = {
		"name":				unicode,	# (string) - The Notebook name is a required field when a creating a Notebook.
		"body":				unicode,	# (text) - The Notebook description.
		"visibility":		int,	# (integer) - Object visibility. 0 marks private visibility and 1 is for normal visibility.
		"milestone_id":		int		# (integer) - The ID of the parent Milestone.
	}
	subpages = []
	project_id = None

	def save(self, **with_extra):
		# will fail if it's a brand new model
		if not Model.save(self, **with_extra) and self.project_id:
			fields = self.get_fields()
			res = self._client.new_notebook(self.project_id, **fields)
			new_fields = res.get_fields()
			self._create_fields(init=new_fields)

class Page(Model):
	method = "notebook_page"
	fields = {
		"name":			unicode,	# (string) - The Notebook Page title is a required value.
		"body":			unicode,	# (text) - The Notebook Page description.
		"parent_id":	int,	# (integer) - The ID of the parent Page. Leave blank to add the page at the 

		"parent_type":	unicode	# not saveable, but is contained within the page json
	}
	subpages = []
	project_id = None
	notebook_id = None # needed for saving the notebook page

	def save(self, **with_extra):
		# will fail if it's a brand new model
		if not Model.save(self, **with_extra) and self.project_id and self.notebook_id:
			fields = self.get_fields()
			res = self._client.new_notebook_page(self.project_id, self.notebook_id, **fields)
			new_fields = res.get_fields()
			self._create_fields(init=new_fields)

class Task(Model):
	id_field = "task_id"
	method = "task"
	fields = {
		"name":				unicode,	# (string) - The Task name is a required field when creating a Task.
		"body":				unicode,	# (text) - The Task description.
		"visibility":		int,	# (integer) - Object visibility. 0 is private and 1 is the value of normal visibility.
		"category_id":		int,	# (integer) - Object category.
		"label_id":			int,	# (integer) - Object label.
		"milestone_id":		int,	# (integer) - ID of the parent Milestone.
		"priority":			int,	# (integer) - The priority can have one of five integer values, ranging from -2 (lowest) to 2 (highest). 0 marks normal.
		"assignee_id":		int,	# (integer) - The user assigned and responsible for the Task.
		"other_assignees":	list,	# (array) - The people assigned to the Task.
		# TODO
		"due_on":			unicode,	# (date) - The task due date.
		"created_by_id":	int,	# (integer) - Use for a known user who already has an account in the system.
		"created_by_name":	unicode,	# (string) - Use for anonymous user, who don't have an account in the system (can not be used with created_by_id).
		"created_by_email":	unicode	# (string) - Used for anonymous users.
	}

	project_id = None

	# the task id of the task - NOT THE SAME AS ITS ID!!!!
	task_id = None

	def save(self, **with_extra):
		# will fail if it's a brand new model
		if not Model.save(self, **with_extra) and self.project_id:
			fields = self.get_fields()
			res = self._client.new_task(self.project_id, **fields)
			new_fields = res.get_fields()
			self._create_fields(init=new_fields)

# TODO subtasks
# body (text) - The Subtask name is required field when creating a new Subtask.
# assignee (integer) - The person assigned to the object.
# priority (integer) - Priority can have five integer values ranging from -2 (lowest) to 2 (highest). 0 is normal priority.
# label_id (date) - Label ID of the Subtask.
# due_on (date) - Date when the subtask is due.

# TODO discussions
# 

class Attachment(Model):
	method = "attachment"
	accept_all_fields = True

	fields = {
		"name":			unicode,
		"size":			int,
		"permalink":	unicode	# this is the download url for the attachment
	}

	def download(self):
		return self._client.download_attachment(self.permalink)
	
class Comment(Model):
	method = "comment"
	fields = {
		"body":				unicode,	# (string) - Comment text
	}

class File(Model):
	method = "file"
	fields = {
		"name": unicode, # (string) - The File name is an optional field when uploading a new file (if omitted, the system will use the original file name of the uploaded file).
		"body": unicode, # (text) - The file description.
		"visibility": int, # (integer) - Object visibility. 0 stands for private, and 1 for normal visibility.
		"milestone_id": int, # (integer) - The ID of the parent Milestone.
		"category_id": int, # (integer) - The Category ID.
	}

	def download(self):
		return self._client.download_file(self)
