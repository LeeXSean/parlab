mod cmd;
mod models;
mod service;
mod utils;
mod views;

use crate::cmd::Cli;
use clap::Parser;
use std::env;
use std::process;

#[tokio::main]

async fn main() {
    // Require POPCORN_API_URL to be set
    let api_url = env::var("POPCORN_API_URL").unwrap_or_else(|_| {
        eprintln!("Error: POPCORN_API_URL environment variable is not set.");
        process::exit(1);
    });

    // For debugging you can print it:
    // println!("Using POPCORN_API_URL = {}", api_url);

    // Parse command line arguments
    let cli = Cli::parse();

    // Execute the parsed command
    if let Err(e) = cmd::execute(cli).await {
        eprintln!("Application error: {}", e);
        process::exit(1);
    }
}
