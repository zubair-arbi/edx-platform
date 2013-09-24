ACCEPTANCE_DB = 'test_root/db/test_edx.db'

def acceptance_dir_path(system)
    return File.join(report_dir_path('acceptance'), system.to_s)
end

[:lms, :cms].each do |system|
    directory acceptance_dir_path(system)
end

def run_acceptance_tests(system, harvest_args)
    # Create the acceptance report directory
    # because if it doesn't exist then lettuce will give an IOError.
    report_dir = acceptance_dir_path(system)

    report_file = File.join(report_dir, "lettucetests.xml")
    report_args = "--with-xunit --xunit-file #{report_file}"
    test_sh(django_admin(system, 'acceptance', 'harvest', '--debug-mode', '--verbosity 2', '--tag -skip', report_args, harvest_args))
end

task :setup_acceptance_db do
    # HACK: Since the CMS depends on the existence of some database tables
    # that are now in common but used to be in LMS (Role/Permissions for Forums)
    # we need to create/migrate the database tables defined in the LMS.
    # We might be able to address this by moving out the migrations from
    # lms/django_comment_client, but then we'd have to repair all the existing
    # migrations from the upgrade tables in the DB.
    # But for now for either system (lms or cms), use the lms
    # definitions to sync and migrate.
    if File.exists?(ACCEPTANCE_DB)
        File.delete(ACCEPTANCE_DB)
    end

    sh(django_admin('lms', 'acceptance', 'syncdb', '--noinput'))
    sh(django_admin('lms', 'acceptance', 'migrate', '--noinput'))
end

task :prep_for_acceptance_tests => [
    :clean_reports_dir, :clean_test_files,
    :install_prereqs, :setup_acceptance_db
]

namespace :test do
    namespace :acceptance do
        task :all, [:harvest_args] => [
            :prep_for_acceptance_tests,
            "^^lms:gather_assets:acceptance",
            "^^cms:gather_assets:acceptance",
            acceptance_dir_path('lms'),
            acceptance_dir_path('cms')
        ] do |t, args|
            run_acceptance_tests('lms', args.harvest_args)
            run_acceptance_tests('cms', args.harvest_args)
        end

        ['lms', 'cms'].each do |system|
            desc "Run the acceptance tests for the #{system}"
            task system, [:harvest_args] => [
                :prep_for_acceptance_tests, acceptance_dir_path(system),
                "^^#{system}:gather_assets:acceptance"
            ] do |t, args|
                args.with_defaults(:harvest_args => '')
                run_acceptance_tests(system, args.harvest_args)
            end

            desc "Run acceptance tests for the #{system} without collectstatic or db migrations"
            task "#{system}:fast", [:harvest_args] => [
                :clean_reports_dir, acceptance_dir_path(system)
            ] do |t, args|
                args.with_defaults(:harvest_args => '')
                run_acceptance_tests(system, args.harvest_args)
            end
        end
    end
    desc "Run the lettuce acceptance tests for lms and cms"
    task :acceptance, [:harvest_args] do |t, args|
      Rake::Task["test:acceptance:all"].invoke(args.harvest_args)
    end
end
