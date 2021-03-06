"""Generic base class for cli hammer commands."""
import logging
import re

from robottelo import ssh
from robottelo.cli import hammer
from robottelo.config import settings


class CLIError(Exception):
    """Indicates that a CLI command could not be run."""


class CLIBaseError(Exception):
    """Indicates that a CLI command has finished with return code different
    from zero.

    :param return_code: CLI command return code
    :param stderr: contents of the ``stderr``
    :param msg: explanation of the error

    """

    def __init__(self, return_code, stderr, msg):
        self.return_code = return_code
        self.stderr = stderr
        self.msg = msg
        super(CLIBaseError, self).__init__(msg)
        self.message = msg

    def __str__(self):
        """Include class name, return_code, stderr and msg to string repr so
        assertRaisesRegexp can be used to assert error present on any
        attribute
        """
        return repr(self)

    def __repr__(self):
        """Include class name return_code, stderr and msg to improve logging
        """
        return '{}(return_code={!r}, stderr={!r}, msg={!r}'.format(
            type(self).__name__, self.return_code, self.stderr, self.msg
        )


class CLIReturnCodeError(CLIBaseError):
    """Error to be raised when an error occurs due to some validation error
    when execution hammer cli.
    See: https://github.com/SatelliteQE/robottelo/issues/3790 for more details
    """


class CLIDataBaseError(CLIBaseError):
    """Error to be raised when an error occurs due to some missing parameter
    which cause a data base error on hammer
    See: https://github.com/SatelliteQE/robottelo/issues/3790 for more details
    """


class Base(object):
    """
    @param command_base: base command of hammer.
    Output of recent `hammer --help`::

        activation-key                Manipulate activation keys.
        architecture                  Manipulate architectures.
        auth                          Foreman connection login/logout.
        auth-source                   Manipulate auth sources.
        bootdisk                      Download boot disks
        capsule                       Manipulate capsule
        compute-resource              Manipulate compute resources.
        content-host                  Manipulate content hosts on the server
        content-report                View Content Reports
        content-view                  Manipulate content views.
        defaults                      Defaults management
        docker                        Manipulate docker content
        domain                        Manipulate domains.
        environment                   Manipulate environments.
        erratum                       Manipulate errata
        fact                          Search facts.
        filter                        Manage permission filters.
        global-parameter              Manipulate global parameters.
        gpg                           Manipulate GPG Key actions on the server
        host                          Manipulate hosts.
        host-collection               Manipulate host collections
        hostgroup                     Manipulate hostgroups.
        import                        Import data exported from a Red Hat Sat..
        lifecycle-environment         Manipulate lifecycle_environments
        location                      Manipulate locations.
        medium                        Manipulate installation media.
        model                         Manipulate hardware models.
        organization                  Manipulate organizations
        os                            Manipulate operating system.
        ostree-branch                 Manipulate ostree branches
        package                       Manipulate packages.
        package-group                 Manipulate package groups
        partition-table               Manipulate partition tables.
        ping                          Get the status of the server
        product                       Manipulate products.
        proxy                         Manipulate smart proxies.
        puppet-class                  Search puppet modules.
        puppet-module                 View Puppet Module details.
        report                        Browse and read reports.
        repository                    Manipulate repositories
        repository-set                Manipulate repository sets on the server
        role                          Manage user roles.
        sc-param                      Manipulate smart class parameters.
        settings                      Change server settings.
        shell                         Interactive shell
        smart-variable                Manipulate smart variables.
        subnet                        Manipulate subnets.
        subscription                  Manipulate subscriptions.
        sync-plan                     Manipulate sync plans
        task                          Tasks related actions.
        template                      Manipulate config templates.
        user                          Manipulate users.
        user-group                    Manage user groups.


    @since: 27.Nov.2013
    """

    command_base = None  # each inherited instance should define this
    command_sub = None  # specific to instance, like: create, update, etc
    command_requires_org = False  # True when command requires organization-id

    logger = logging.getLogger('robottelo')
    _db_error_regex = re.compile(r'.*INSERT INTO|.*SELECT .*FROM|.*violates foreign key')

    @classmethod
    def _handle_response(cls, response, ignore_stderr=None):
        """Verify ``return_code`` of the CLI command.

        Check for a non-zero return code or any stderr contents.

        :param response: a ``SSHCommandResult`` object, returned by
            :mod:`robottelo.ssh.command`.
        :param ignore_stderr: indicates whether to throw a warning in logs if
            ``stderr`` is not empty.
        :returns: contents of ``stdout``.
        :raises robottelo.cli.base.CLIReturnCodeError: If return code is
            different from zero.
        """
        if response.return_code != 0:
            full_msg = (
                'Command "{0} {1}" finished with return_code {2}\n'
                'stderr contains following message:\n{3}'.format(
                    cls.command_base, cls.command_sub, response.return_code, response.stderr
                )
            )
            error_data = (response.return_code, response.stderr, full_msg)
            if cls._db_error_regex.search(full_msg):
                raise CLIDataBaseError(*error_data)
            raise CLIReturnCodeError(*error_data)
        if len(response.stderr) != 0 and not ignore_stderr:
            cls.logger.warning('stderr contains following message:\n{0}'.format(response.stderr))
        return response.stdout

    @classmethod
    def add_operating_system(cls, options=None):
        """
        Adds OS to record.
        """

        cls.command_sub = 'add-operatingsystem'

        result = cls.execute(cls._construct_command(options))

        return result

    @classmethod
    def create(cls, options=None, timeout=None):
        """
        Creates a new record using the arguments passed via dictionary.
        """

        cls.command_sub = 'create'

        if options is None:
            options = {}

        result = cls.execute(cls._construct_command(options), output_format='csv', timeout=timeout)

        # Extract new object ID if it was successfully created
        if len(result) > 0 and 'id' in result[0]:
            obj_id = result[0]['id']

            # Fetch new object
            # Some Katello obj require the organization-id for subcommands
            info_options = {'id': obj_id}
            if cls.command_requires_org:
                if 'organization-id' not in options:
                    tmpl = 'organization-id option is required for {0}.create'
                    raise CLIError(tmpl.format(cls.__name__))
                info_options['organization-id'] = options['organization-id']

            new_obj = cls.info(info_options)
            # stdout should be a dictionary containing the object
            if len(new_obj) > 0:
                result = new_obj

        return result

    @classmethod
    def delete(cls, options=None, timeout=None):
        """Deletes existing record."""
        cls.command_sub = 'delete'
        return cls.execute(cls._construct_command(options), ignore_stderr=True, timeout=timeout)

    @classmethod
    def delete_parameter(cls, options=None):
        """
        Deletes parameter from record.
        """

        cls.command_sub = 'delete-parameter'

        result = cls.execute(cls._construct_command(options))

        return result

    @classmethod
    def dump(cls, options=None):
        """
        Displays the content for existing partition table.
        """

        cls.command_sub = 'dump'

        result = cls.execute(cls._construct_command(options))

        return result

    @classmethod
    def _get_username_password(cls, username=None, password=None):
        """Lookup for the username and password for cli command in following
        order:

        1. ``user`` or ``password`` parameters
        2. ``foreman_admin_username`` or ``foreman_admin_password`` attributes
        3. foreman.admin.username or foreman.admin.password configuration

        :return: A tuple with the username and password found
        :rtype: tuple

        """
        if username is None:
            try:
                username = getattr(cls, 'foreman_admin_username')
            except AttributeError:
                username = settings.server.admin_username
        if password is None:
            try:
                password = getattr(cls, 'foreman_admin_password')
            except AttributeError:
                password = settings.server.admin_password

        return (username, password)

    @classmethod
    def execute(
        cls,
        command,
        user=None,
        password=None,
        output_format=None,
        timeout=None,
        ignore_stderr=None,
        return_raw_response=None,
        connection_timeout=None,
    ):
        """Executes the cli ``command`` on the server via ssh"""
        user, password = cls._get_username_password(user, password)
        time_hammer = False
        if settings.performance:
            time_hammer = settings.performance.time_hammer

        # add time to measure hammer performance
        cmd = 'LANG={0} {1} hammer -v {2} {3} {4} {5}'.format(
            settings.locale,
            'time -p' if time_hammer else '',
            '-u {0}'.format(user) if user is not None else '--interactive no',
            '-p {0}'.format(password) if password is not None else '',
            '--output={0}'.format(output_format) if output_format else '',
            command,
        )
        response = ssh.command(
            cmd.encode('utf-8'),
            output_format=output_format,
            timeout=timeout,
            connection_timeout=connection_timeout,
        )
        if return_raw_response:
            return response
        else:
            return cls._handle_response(response, ignore_stderr=ignore_stderr)

    @classmethod
    def exists(cls, options=None, search=None):
        """Search for an entity using the query ``search[0]="search[1]"``

        Will be used the ``list`` command with the ``--search`` option to do
        the search.

        If ``options`` argument already have a search key, then the ``search``
        argument will not be evaluated. Which allows different search query.

        """

        if options is None:
            options = {}

        if search is not None and 'search' not in options:
            options.update({'search': '{0}=\\"{1}\\"'.format(search[0], search[1])})

        result = cls.list(options)
        if result:
            result = result[0]

        return result

    @classmethod
    def info(cls, options=None, output_format=None, return_raw_response=None):
        """Reads the entity information."""
        cls.command_sub = 'info'

        if options is None:
            options = {}

        if cls.command_requires_org and 'organization-id' not in options:
            raise CLIError('organization-id option is required for {0}.info'.format(cls.__name__))

        result = cls.execute(
            command=cls._construct_command(options),
            output_format=output_format,
            return_raw_response=return_raw_response,
        )
        if not return_raw_response and output_format != 'json':
            result = hammer.parse_info(result)
        return result

    @classmethod
    def list(cls, options=None, per_page=True, output_format='csv'):
        """
        List information.
        @param options: ID (sometimes name works as well) to retrieve info.
        """

        cls.command_sub = 'list'

        if options is None:
            options = {}

        if 'per-page' not in options and per_page:
            options['per-page'] = 10000

        if cls.command_requires_org and 'organization-id' not in options:
            raise CLIError('organization-id option is required for {0}.list'.format(cls.__name__))

        result = cls.execute(cls._construct_command(options), output_format=output_format)

        return result

    @classmethod
    def puppetclasses(cls, options=None):
        """
        Lists all puppet classes.
        """

        cls.command_sub = 'puppet-classes'

        result = cls.execute(cls._construct_command(options), output_format='csv')

        return result

    @classmethod
    def remove_operating_system(cls, options=None):
        """
        Removes OS from record.
        """

        cls.command_sub = 'remove-operatingsystem'

        result = cls.execute(cls._construct_command(options))

        return result

    @classmethod
    def sc_params(cls, options=None):
        """
        Lists all smart class parameters.
        """

        cls.command_sub = 'sc-params'

        result = cls.execute(cls._construct_command(options), output_format='csv')

        return result

    @classmethod
    def set_parameter(cls, options=None):
        """
        Creates or updates parameter for a record.
        """

        cls.command_sub = 'set-parameter'

        result = cls.execute(cls._construct_command(options))

        return result

    @classmethod
    def update(cls, options=None, return_raw_response=None):
        """
        Updates existing record.
        """

        cls.command_sub = 'update'

        result = cls.execute(
            cls._construct_command(options),
            output_format='csv',
            return_raw_response=return_raw_response,
        )

        return result

    @classmethod
    def with_user(cls, username=None, password=None):
        """Context Manager for credentials"""

        class Wrapper(cls):
            """Wrapper class which defines the foreman admin username and
            password to be used when executing any cli command.

            """

            foreman_admin_username = username
            foreman_admin_password = password

        return Wrapper

    @classmethod
    def _construct_command(cls, options=None):
        """Build a hammer cli command based on the options passed"""
        tail = ''

        if options is None:
            options = {}

        for key, val in options.items():
            if val is None:
                continue
            if val is True:
                tail += ' --{0}'.format(key)
            elif val is not False:
                if isinstance(val, list):
                    val = ','.join(str(el) for el in val)
                tail += ' --{0}="{1}"'.format(key, val)
        cmd = '{0} {1} {2}'.format(cls.command_base, cls.command_sub, tail.strip())

        return cmd
