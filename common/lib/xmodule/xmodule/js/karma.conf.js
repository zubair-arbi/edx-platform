module.exports = function(config) {
    config.set({
        basePath: '',
        frameworks: ['jasmine'],
        browsers: ['Firefox'],
        files: [

            // Libraries
            '../../../../static/coffee/src/ajax_prefix.js',
            '../../../../static/coffee/src/logger.js',
            '../../../../static/js/vendor/jasmine-jquery.js',
            '../../../../static/js/vendor/require.js',
            'RequireJS-namespace-undefine.js',
            '../../../../static/js/vendor/jquery.min.js',
            '../../../../static/js/vendor/jquery-ui.min.js',
            '../../../../static/js/vendor/jquery.ui.draggable.js',
            '../../../../static/js/vendor/jquery.cookie.js',
            '../../../../static/js/vendor/json2.js',
            '../../../../static/js/vendor/underscore-min.js',
            '../../../../static/js/vendor/backbone-min.js',
            '../../../../static/js/vendor/jquery.leanModal.min.js',
            '../../../../static/js/vendor/CodeMirror/codemirror.js',
            '../../../../static/js/vendor/tiny_mce/jquery.tinymce.js',
            '../../../../static/js/vendor/tiny_mce/tiny_mce.js',
            '../../../../static/js/vendor/mathjax-MathJax-c9db6ac/MathJax.js',
            {pattern: '../../../../static/js/vendor/mathjax-MathJax-c9db6ac/extensions/**/*.js', included:false},
            '../../../../static/js/vendor/jquery.timeago.js',
            '../../../../static/js/vendor/sinon-1.7.1.js',
            '../../../../static/js/vendor/analytics.js',
            '../../../../static/js/test/add_ajax_prefix.js',
            '../../../../static/js/src/utility.js',

            // Sources
            'src/xmodule.js',
            'src/**/*.js',

            // Test fixtures
            {pattern: 'fixtures/*', included:false},
            
            // Tests
            'spec/helper.js',
            'spec/**/*.js'
        ],
        exclude: [
            "src/word_cloud/d3.layout.cloud.js"
        ],
        preprocessors: {}
    });
};
