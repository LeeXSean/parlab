use anyhow::{anyhow, Result};
use clap::{Parser, Subcommand};
use dirs;
use serde::{Deserialize, Serialize};
use serde_yaml;
use std::fs::File;
use std::path::PathBuf;

mod auth;
mod submit;

#[derive(Serialize, Deserialize, Debug, Default)]
struct Config {
    cli_id: Option<String>,
    sunet_id: Option<String>,
    nickname: Option<String>
}

fn get_config_path() -> Result<PathBuf> {
    dirs::home_dir()
        .map(|mut path| {
            path.push(".popcorn.yaml");
            path
        })
        .ok_or_else(|| anyhow!("Could not find home directory"))
}

fn load_config() -> Result<Config> {
    let path = get_config_path()?;
    if !path.exists() {
        return Err(anyhow!(
            "Config file not found at {}. Please run `popcorn register` first.",
            path.display()
        ));
    }
    let file = File::open(path)?;
    serde_yaml::from_reader(file).map_err(|e| anyhow!("Failed to parse config file: {}", e))
}

#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
pub struct Cli {
    #[command(subcommand)]
    command: Option<Commands>,

    /// Optional: Path to the solution file
    filepath: Option<String>,

    // #[arg(long)]
    #[arg(long, hide = true, default_value = "H100")]
    pub gpu: Option<String>,

    /// Optional: Directly specify the leaderboard
    #[arg(long)]
    pub leaderboard: Option<String>,

    /// Optional: Specify submission mode (test, benchmark, leaderboard, profile)
    #[arg(long)]
    pub mode: Option<String>,

    // Optional: Specify output file
    #[arg(short, long)]
    pub output: Option<String>,
}

#[derive(Subcommand, Debug)]
enum AuthProvider {
    // Discord,
    Github,
}

#[derive(Subcommand, Debug)]
enum Commands {
    // Reregister {
    //     #[command(subcommand)]
    //     provider: AuthProvider,

    //     #[arg(long)]
    //     sunet_id: String,

    //     #[arg(long)]
    //     nickname: String,
    // },
    Register {
        // #[command(subcommand)]
        // provider: AuthProvider,
       
        #[arg(long)]
        sunet_id: String,

        #[arg(long)]
        nickname: String,
    },
    Submit {
        /// Optional: Path to the solution file (can also be provided as a top-level argument)
        filepath: Option<String>,
        
        /// Deprecated
        // #[arg(long)]
        #[arg(long, hide = true, default_value = "H100")]
        gpu: Option<String>,

        /// Optional: Directly specify the leaderboard
        #[arg(long)]
        leaderboard: Option<String>,

        /// Optional: Specify submission mode (test, benchmark, leaderboard, profile)
        #[arg(long)]
        mode: Option<String>,

        // Optional: Specify output file
        #[arg(short, long)]
        output: Option<String>,
    },
}

pub async fn execute(cli: Cli) -> Result<()> {
    match cli.command {
        // Some(Commands::Reregister { provider, sunet_id, nickname }) => {
        //     let provider_str = match provider {
        //         AuthProvider::Discord => "discord",
        //         AuthProvider::Github => "github",
        //     };
        //     auth::run_auth(true, provider_str, sunet_id, nickname).await
        // }
        Some(Commands::Register { sunet_id, nickname }) => {
            // let provider_str = match provider {
            //     AuthProvider::Discord => "discord",
            //     AuthProvider::Github => "github",
            // };
            let provider_str = "github";
            auth::run_auth(false, provider_str, sunet_id, nickname).await
        }
        Some(Commands::Submit {
            filepath,
            gpu,
            leaderboard,
            mode,
            output,
        }) => {
            let config = load_config()?;
            let cli_id = config.cli_id.ok_or_else(|| {
                anyhow!(
                    "cli_id not found in config file ({}). Please run 'popcorn-cli register' first.",
                    get_config_path()
                        .map_or_else(|_| "unknown path".to_string(), |p| p.display().to_string())
                )
            })?;

            // Use filepath from Submit command first, fallback to top-level filepath
            let final_filepath: Option<String> = filepath.or(cli.filepath);
            // let final_filepath: Option<String> = filepath.on(cli.filepath);
            // let final_filepath: String = filepath;
            submit::run_submit_tui(
                final_filepath, // Resolved filepath
                gpu,            // From Submit command
                leaderboard,    // From Submit command
                mode,           // From Submit command
                cli_id,
                output, // From Submit command
            )
            .await
        }
        // None => {  // ← MAKE SURE THIS ARM EXISTS
        //     Err(anyhow!("No command specified. Use --help for usage."))
        // }
        None => {
            // Check if any of the submission-related flags were used at the top level
            if cli.gpu.is_some() || cli.leaderboard.is_some() || cli.mode.is_some() {
                return Err(anyhow!(
                    "Please use the 'submit' subcommand when specifying submission options:\n\
                    popcorn-cli submit [--gpu GPU] [--leaderboard LEADERBOARD] [--mode MODE] FILEPATH"
                ));
            }

            // Handle the case where only a filepath is provided (for backward compatibility)
            if let Some(top_level_filepath) = cli.filepath {
                let config = load_config()?;
                let cli_id = config.cli_id.ok_or_else(|| {
                    anyhow!(
                        "cli_id not found in config file ({}). Please run `popcorn register` first.",
                        get_config_path()
                            .map_or_else(|_| "unknown path".to_string(), |p| p.display().to_string())
                    )
                })?;

                // Run TUI with only filepath, no other options
                submit::run_submit_tui(
                    Some(top_level_filepath),
                    None, // No GPU option
                    None, // No leaderboard option
                    None, // No mode option
                    cli_id,
                    None, // No output option
                )
                .await
            } else {
                Err(anyhow!("No command or submission file specified. Use --help for usage."))
            }
        }
    }
}
