const path = require('path')
const ExtractTextPlugin = require('extract-text-webpack-plugin')
const LiveReloadPlugin = require('webpack-livereload-plugin')
const webpack = require('webpack')

const extractSass = new ExtractTextPlugin({
  filename: '../css/[name].css',
  disable: process.env.NODE_ENV === 'development'
})

const config = {
  entry: {
    main: './frontend/javascript/main.js'
  },
  output: {
    path: path.resolve(__dirname, 'froide/static/js'),
    filename: '[name].js',
    library: ['Froide', 'components', '[name]'],
    libraryTarget: 'umd'
  },
  devtool: 'source-map', // any "source-map"-like devtool is possible
  resolve: {
    modules: ['node_modules', 'froide/static'],
    extensions: ['.js', '.vue', '.json'],
    alias: {
      'vue$': 'vue/dist/vue.esm.js'
    }
  },
  module: {
    rules: [{
      test: /\.js$/,
      exclude: /(node_modules|bower_components)/,
      use: {
        loader: 'babel-loader'
      }
    },
    {
      test: /\.vue/,
      use: {
        loader: 'vue-loader'
      }
    },
    {
      test: /\.scss$/,
      use: extractSass.extract({
        use: [{
          loader: 'css-loader',
          options: {
            sourceMap: true
          }
        },
        {
          loader: 'sass-loader',
          options: {
            sourceMap: true,
            includePaths: ['node_modules/']
          }
        }],
        // use style-loader in development
        fallback: 'style-loader'
      })
    },
    {
      test: /(\.(woff2?|eot|ttf|otf)|font\.svg)(\?.*)?$/,
      loader: 'url-loader',
      options: {
        limit: 10000,
        name: '../fonts/[name].[ext]',
        emitFile: true,
        context: 'froide/static/',
        publicPath: ''
      }
    },
    {
      test: /\.(jpg|png)$/,
      use: {
        loader: 'url-loader',
        options: {
          limit: 8192,
          name: '[path][name].[ext]',
          emitFile: false,
          context: 'froide/static',
          publicPath: '../'
        }
      }
    }
    ]
  },
  plugins: [
    extractSass,
    new LiveReloadPlugin(),
    new webpack.ProvidePlugin({
      $: 'jquery',
      jQuery: 'jquery',
      Popper: ['popper.js/dist/popper.js', 'default']
    })
  ]
};

module.exports = config;
